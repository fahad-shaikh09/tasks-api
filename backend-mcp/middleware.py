"""
ASGI auth middleware for the MCP server.

Sits in front of FastMCP's HTTP transport. For every incoming request:
  1. Pull the Cookie header.
  2. Hand it to the shared session validator (calls auth-service).
  3. If valid, stash the AuthUser in a contextvar that tool handlers read.
  4. If invalid, return 401 so the agent's MCP client gets a clear signal.

Health and DAP probe paths are allowed through unauthenticated.
"""

from __future__ import annotations

import logging
from typing import Iterable

from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.auth import validate_session
from auth_context import current_user_var

logger = logging.getLogger(__name__)

# Paths that should never require auth (probes, dapr discovery, etc.)
DEFAULT_PUBLIC_PATHS: tuple[str, ...] = (
    "/healthz",
    "/dapr/subscribe",
    "/dapr/config",
)


class SessionAuthMiddleware:
    def __init__(self, app: ASGIApp, public_paths: Iterable[str] = DEFAULT_PUBLIC_PATHS):
        self.app = app
        self.public_paths = tuple(public_paths)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path: str = scope.get("path", "")
        if path in self.public_paths:
            await self.app(scope, receive, send)
            return

        cookie_header = _read_cookie_header(scope.get("headers", []))
        user = await validate_session(cookie_header)
        if user is None:
            await _send_401(send)
            return

        token = current_user_var.set(user)
        try:
            await self.app(scope, receive, send)
        finally:
            current_user_var.reset(token)


def _read_cookie_header(headers: list[tuple[bytes, bytes]]) -> str | None:
    for name, value in headers:
        if name == b"cookie":
            return value.decode("latin-1")
    return None


async def _send_401(send: Send) -> None:
    body = b'{"error":"unauthenticated"}'
    await send({
        "type": "http.response.start",
        "status": 401,
        "headers": [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(body)).encode()),
        ],
    })
    await send({"type": "http.response.body", "body": body})
