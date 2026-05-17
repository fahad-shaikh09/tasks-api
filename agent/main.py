#!/usr/bin/env python3
"""
AI Task Manager Agent — Web UI

A browser-based chat agent that uses the OpenAI Agents SDK + Chainlit
to manage tasks via our MCP server running in OpenShift.

Architecture:
    Browser (Chainlit UI, port 8000)
      → Agent (OpenAI Agents SDK)
        → OpenAI API (GPT model decides which tool to call)
          → MCP Server (http://mcp-server:8001/mcp, executes the tool)
            → back to GPT (formulates a human-friendly answer)
              → displayed in the browser chat

    Notifications flow:
      Task action → Kafka event → Notification Service
      The browser polls /api/notifications/count and renders a bell
      icon with badge + dropdown (see public/notif-bell.js). Nothing
      is injected into the chat transcript.

Usage:
    Runs inside OpenShift. Access via the Route URL in your browser.
"""

import os
import logging

import httpx
import chainlit as cl
from agents import Agent, Runner
from agents.mcp import MCPServerStreamableHttp
from chainlit.server import app as fastapi_app
from fastapi.routing import APIRoute

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tasks_agent")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://mcp-server:8001/mcp")
NOTIFICATION_SERVICE_URL = os.getenv(
    "NOTIFICATION_SERVICE_URL", "http://notification:8002"
)

# System instructions — now includes notification tools
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
# Notification proxy endpoints
#
# The bell icon in the browser (public/notif-bell.js) calls these same-origin
# endpoints. We proxy through to the notification microservice so the browser
# never needs to know the in-cluster service URL or deal with CORS.
#
# IMPORTANT: Chainlit registers a catch-all "/{path:path}" route that serves
# the SPA's index.html. If we just decorate with @fastapi_app.get(...), our
# routes get appended AFTER the catch-all and never match — the browser gets
# HTML instead of JSON. We define the handlers here and then insert them at
# the FRONT of the router below.
# ---------------------------------------------------------------------------

async def _api_list_notifications():
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{NOTIFICATION_SERVICE_URL}/notifications", timeout=5.0
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.warning(f"Failed to fetch notifications: {e}")
        return []


async def _api_notification_count():
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{NOTIFICATION_SERVICE_URL}/notifications", timeout=5.0
            )
            response.raise_for_status()
            return {"count": len(response.json())}
    except Exception:
        return {"count": 0}


async def _api_clear_notifications():
    try:
        async with httpx.AsyncClient() as client:
            await client.delete(
                f"{NOTIFICATION_SERVICE_URL}/notifications", timeout=5.0
            )
    except Exception as e:
        logger.warning(f"Failed to clear notifications: {e}")
    return {"status": "ok"}


# Prepend so these match before Chainlit's SPA catch-all.
# Order in the list = order matched (insert(0, ...) reverses, so we iterate
# in reverse to preserve the intended order in the routing table).
_notif_routes = [
    APIRoute("/api/notifications/count", _api_notification_count, methods=["GET"]),
    APIRoute("/api/notifications", _api_list_notifications, methods=["GET"]),
    APIRoute("/api/notifications", _api_clear_notifications, methods=["DELETE"]),
]
for _r in reversed(_notif_routes):
    fastapi_app.router.routes.insert(0, _r)


# ---------------------------------------------------------------------------
# Chainlit lifecycle hooks
# ---------------------------------------------------------------------------

@cl.on_chat_start
async def on_chat_start():
    """
    Fires when a user opens the chat in their browser.
    Connects to MCP, creates the agent, and initializes notification tracking.
    """
    mcp_server = MCPServerStreamableHttp(
        name="Tasks MCP Server",
        params={"url": MCP_SERVER_URL},
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

    logger.info(f"Session started — connected to MCP at {MCP_SERVER_URL}")

    await cl.Message(
        content=(
            "Hello! I'm your Task Manager assistant. "
            "I can help you create, view, update, and delete tasks.\n\n"
            "You can also ask me to show notifications or recent activity.\n\n"
            "What would you like to do?"
        )
    ).send()


@cl.on_chat_end
async def on_chat_end():
    """Clean up the MCP server connection when the user leaves."""
    mcp_server = cl.user_session.get("mcp_server")
    if mcp_server:
        await mcp_server.__aexit__(None, None, None)
        logger.info("Session ended — MCP connection closed")


@cl.on_message
async def on_message(message: cl.Message):
    """Fires on every user message. Notifications are surfaced via the
    bell icon in the UI, not injected into the chat transcript."""
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
