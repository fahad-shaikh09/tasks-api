#!/usr/bin/env python3
"""
AI Task Manager Agent — Web UI

A browser-based chat agent that uses the OpenAI Agents SDK + Chainlit
to manage tasks via our MCP server running in OpenShift.

Architecture:
    Browser (Chainlit UI, port 8000)
      → Agent (OpenAI Agents SDK)
        → OpenAI API
          → MCP Server (http://mcp-server:8001/mcp)
            → executes the tool
              → back to GPT
                → displayed in the browser chat

    Auth:
      Unauthenticated GET / is redirected to {AUTH_SERVICE_URL}/login.
      The browser logs in, gets a session cookie scoped to
      .apps-crc.testing, and is bounced back here. Chainlit's
      header_auth_callback validates that cookie via the shared
      auth-service. The validated cookie is also forwarded to the
      MCP server so it knows who the user is.

    Notifications:
      Browser polls /api/notifications/count (proxied through this app
      to the notification service, scoped by user_id derived from the
      session cookie).
"""

import os
import logging
from typing import Optional

import httpx
import chainlit as cl
from agents import Agent, Runner
from agents.mcp import MCPServerStreamableHttp
from chainlit.server import app as fastapi_app
from fastapi.routing import APIRoute
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from auth_client import validate_session, AUTH_SERVICE_URL

# Public URL of auth-service (what the browser uses). Inside the cluster
# we hit AUTH_SERVICE_URL (svc DNS), but redirects must point at the
# externally reachable route. Falls back to AUTH_SERVICE_URL for local dev.
AUTH_SERVICE_PUBLIC_URL = os.getenv("AUTH_SERVICE_PUBLIC_URL", AUTH_SERVICE_URL)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tasks_agent")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://mcp-server:8001/mcp")
NOTIFICATION_SERVICE_URL = os.getenv(
    "NOTIFICATION_SERVICE_URL", "http://notification:8002"
)

AGENT_INSTRUCTIONS = """
You are a helpful task management assistant. You help users create,
view, update, and delete tasks using natural language.

You have access to these tools via MCP:
- create_task: Create a new task (requires title and description)
- list_tasks: List tasks, optionally filtered by status
- get_task: Get a specific task by its ID
- update_task: Update a task's title, description, or status
- delete_task: Delete a task by its ID
- list_notifications: View recent notifications (task events)
- clear_notifications: Clear all notifications

When a user asks to manage tasks, use the appropriate tool.
Always confirm what you did after performing an action.
If a user asks about notifications or recent activity, use list_notifications.
If a user's request is ambiguous, ask for clarification.
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _user_from_request(request: Request):
    """Validate the incoming request's session cookie."""
    return await validate_session(request.headers.get("cookie"))


# ---------------------------------------------------------------------------
# Auth-gate middleware
#
# For HTML-page requests ("/", "/login", etc.) with no valid session, send
# the browser to the auth-service login page. API endpoints get a 401 JSON.
# ---------------------------------------------------------------------------

# Paths that should NEVER be gated — static assets, our own API, websockets,
# Chainlit internals, etc.
_OPEN_PREFIXES = (
    "/public/",
    "/static/",
    "/assets/",
    "/favicon",
    "/logo",
    "/ws",                   # Chainlit websocket
    "/socket.io",
    "/api/notifications",    # has its own per-request cookie check below
    "/healthz",
)

# Paths that are HTML pages — unauthenticated hits get a 302 redirect.
_HTML_GATE_PATHS = ("/",)


class AuthGateMiddleware:
    """Redirects browser hits to login when the session is missing/invalid."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path: str = scope.get("path", "")
        if any(path.startswith(p) for p in _OPEN_PREFIXES):
            await self.app(scope, receive, send)
            return

        if path not in _HTML_GATE_PATHS:
            await self.app(scope, receive, send)
            return

        # GET / — check cookie, redirect to /login if invalid
        cookie = _read_cookie(scope.get("headers", []))
        user = await validate_session(cookie)
        if user is not None:
            await self.app(scope, receive, send)
            return

        # Build redirect to the auth-service login page, preserving where
        # we want to land afterwards (this agent's own URL).
        # We use the Host header so the redirect target works whether the
        # cluster route uses HTTP or HTTPS.
        host = _read_header(scope.get("headers", []), b"host") or b""
        scheme = scope.get("scheme", "http")
        return_to = f"{scheme}://{host.decode('latin-1')}/"
        login_url = f"{AUTH_SERVICE_PUBLIC_URL}/login?redirect={return_to}"

        resp = RedirectResponse(login_url, status_code=302)
        await resp(scope, receive, send)


def _read_cookie(headers: list[tuple[bytes, bytes]]) -> Optional[str]:
    for name, value in headers:
        if name == b"cookie":
            return value.decode("latin-1")
    return None


def _read_header(headers: list[tuple[bytes, bytes]], key: bytes) -> Optional[bytes]:
    for name, value in headers:
        if name == key:
            return value
    return None


# Wrap the Chainlit ASGI app. Starlette mutates user_middleware lazily, so
# inserting at app startup is fine.
fastapi_app.add_middleware(AuthGateMiddleware)


# ---------------------------------------------------------------------------
# Notification proxy endpoints (bell icon)
#
# Each call reads the session cookie, validates it, then asks the
# notification service for THIS user's notifications only.
# Routes are prepended so they win over Chainlit's SPA catch-all.
# ---------------------------------------------------------------------------

async def _api_list_notifications(request: Request):
    user = await _user_from_request(request)
    if user is None:
        return JSONResponse({"error": "unauthenticated"}, status_code=401)
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{NOTIFICATION_SERVICE_URL}/notifications",
                params={"user_id": user.id},
                timeout=5.0,
            )
            response.raise_for_status()
            return JSONResponse(response.json())
    except Exception as e:
        logger.warning(f"Failed to fetch notifications: {e}")
        return JSONResponse([])


async def _api_notification_count(request: Request):
    user = await _user_from_request(request)
    if user is None:
        return JSONResponse({"count": 0})
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{NOTIFICATION_SERVICE_URL}/notifications",
                params={"user_id": user.id},
                timeout=5.0,
            )
            response.raise_for_status()
            return JSONResponse({"count": len(response.json())})
    except Exception:
        return JSONResponse({"count": 0})


async def _api_clear_notifications(request: Request):
    user = await _user_from_request(request)
    if user is None:
        return JSONResponse({"error": "unauthenticated"}, status_code=401)
    try:
        async with httpx.AsyncClient() as client:
            await client.delete(
                f"{NOTIFICATION_SERVICE_URL}/notifications",
                params={"user_id": user.id},
                timeout=5.0,
            )
    except Exception as e:
        logger.warning(f"Failed to clear notifications: {e}")
    return JSONResponse({"status": "ok"})


async def _api_logout(request: Request):
    """Combined logout: invalidate better-auth session AND clear the cookie.

    Chainlit's built-in /logout only clears its own state; the
    better-auth session cookie on .apps-crc.testing survives, so on
    page reload `header_auth_callback` sees the still-valid cookie
    and silently re-authenticates. We override /logout to also call
    better-auth's sign-out (server-side invalidation) and emit a
    cookie-clearing Set-Cookie on the shared domain.
    """
    cookie = request.headers.get("cookie") or ""

    if cookie:
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{AUTH_SERVICE_URL}/api/auth/sign-out",
                    headers={"Cookie": cookie},
                    timeout=5.0,
                )
        except Exception as e:
            logger.warning(f"logout: auth-service sign-out failed: {e}")

    resp = JSONResponse({"success": True})

    # Clear every cookie the browser sent us. Two reasons we can't just
    # delete the better-auth one:
    #  - Chainlit keeps its own session cookies (the names vary across
    #    versions) and reuses the cached cl.User if they survive — so a
    #    different user signing in still sees the previous user.
    #  - We want a clean slate on sign-out regardless of what's set.
    # The better-auth cookie lives on .apps-crc.testing; everything else
    # is host-scoped (no Domain attribute).
    for name in request.cookies:
        if name == "better-auth.session_token":
            resp.delete_cookie(name, domain=".apps-crc.testing", path="/")
        else:
            resp.delete_cookie(name, path="/")

    return resp


_notif_routes = [
    APIRoute("/logout", _api_logout, methods=["POST"]),
    APIRoute("/api/notifications/count", _api_notification_count, methods=["GET"]),
    APIRoute("/api/notifications", _api_list_notifications, methods=["GET"]),
    APIRoute("/api/notifications", _api_clear_notifications, methods=["DELETE"]),
]
for _r in reversed(_notif_routes):
    fastapi_app.router.routes.insert(0, _r)


# ---------------------------------------------------------------------------
# Chainlit auth callback — gates the websocket connection
# ---------------------------------------------------------------------------

@cl.header_auth_callback
async def header_auth(headers) -> Optional[cl.User]:
    """Validate the session cookie at WebSocket upgrade time.

    Chainlit gives us the raw headers dict. If we return None, the chat
    session is rejected. If we return a cl.User, Chainlit considers the
    user authenticated and stashes the user on cl.user_session.

    We stash the cookie on the user metadata too — `on_chat_start` needs
    to forward it to the MCP server, and Chainlit's `context.session.http_headers`
    doesn't reliably expose Cookie across versions.
    """
    cookie = headers.get("cookie") or headers.get("Cookie") or ""
    user = await validate_session(cookie)
    if user is None:
        return None
    # Chainlit renders `identifier` in the avatar/header, so prefer the
    # human-readable name (then email) over the opaque better-auth id.
    display = user.name or user.email or user.id
    return cl.User(
        identifier=display,
        metadata={
            "id": user.id,
            "email": user.email or "",
            "name": user.name or "",
        },
    )


# ---------------------------------------------------------------------------
# Chainlit lifecycle hooks
# ---------------------------------------------------------------------------

@cl.on_chat_start
async def on_chat_start():
    """Open an MCP session that forwards the user's auth cookie to the server."""
    cl_user: cl.User | None = cl.user_session.get("user")  # set by Chainlit auth

    # Forward the browser's session cookie to the MCP server. This is how
    # the MCP server's middleware learns which user is calling each tool.
    cookie = _extract_cookie_from_chainlit() or ""

    mcp_server = MCPServerStreamableHttp(
        name="Tasks MCP Server",
        params={
            "url": MCP_SERVER_URL,
            "headers": {"Cookie": cookie} if cookie else {},
        },
        cache_tools_list=True,
    )
    await mcp_server.__aenter__()

    agent = Agent(
        name="Task Manager",
        instructions=AGENT_INSTRUCTIONS,
        mcp_servers=[mcp_server],
    )

    cl.user_session.set("mcp_server", mcp_server)
    cl.user_session.set("agent", agent)

    who = cl_user.identifier if cl_user else "unknown"
    logger.info(f"Session started for user={who} — MCP={MCP_SERVER_URL}")

    name = (cl_user.metadata or {}).get("name") if cl_user else None
    greeting = f"Hello {name}!" if name else "Hello!"
    await cl.Message(
        content=(
            f"{greeting} I'm your Task Manager assistant. "
            "I can help you create, view, update, and delete tasks.\n\n"
            "What would you like to do?"
        )
    ).send()


def _extract_cookie_from_chainlit() -> Optional[str]:
    """Pull the upgrade-request Cookie header off Chainlit's session.

    Chainlit's WebsocketSession exposes the socket.io environ, where the
    upgrade Cookie header is stored as `HTTP_COOKIE`. `http_headers` is
    not reliably populated in the version we ship, so prefer environ.
    """
    try:
        from chainlit.context import context
        sess = context.session

        environ = getattr(sess, "environ", None) or {}
        cookie = environ.get("HTTP_COOKIE")
        if cookie:
            return cookie

        ws_headers = getattr(sess, "http_headers", None) or {}
        return ws_headers.get("cookie") or ws_headers.get("Cookie")
    except Exception as e:  # noqa: BLE001
        logger.warning("cookie extract failed: %r", e)
        return None


@cl.on_chat_end
async def on_chat_end():
    """Clean up the MCP server connection when the user leaves."""
    mcp_server = cl.user_session.get("mcp_server")
    if mcp_server:
        await mcp_server.__aexit__(None, None, None)
        logger.info("Session ended — MCP connection closed")


@cl.on_message
async def on_message(message: cl.Message):
    """Forward the user message to the agent."""
    agent = cl.user_session.get("agent")
    if not agent:
        await cl.Message(content="Session not initialized. Please refresh the page.").send()
        return

    msg = cl.Message(content="")
    await msg.send()

    try:
        result = await Runner.run(agent, message.content)
        msg.content = result.final_output
        await msg.update()
    except Exception as e:
        logger.error(f"Agent error: {e}", exc_info=True)
        msg.content = f"Sorry, something went wrong: {e}"
        await msg.update()
