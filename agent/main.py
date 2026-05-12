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

How it works:
    1. When a user opens the chat, @cl.on_chat_start fires.
       We connect to the MCP server and discover available tools.

    2. When the user sends a message, @cl.on_message fires.
       We pass the message to Runner.run(), which:
       - Sends it to the OpenAI API along with the tool definitions
       - The LLM decides if it needs to call a tool (e.g. create_task)
       - If yes, the SDK calls the tool on our MCP server over HTTP
       - The tool result goes back to the LLM for a final answer

    3. The final answer is displayed in the Chainlit chat UI.

Usage:
    Runs inside OpenShift. Access via the Route URL in your browser.
"""

import os
import logging

import chainlit as cl
from agents import Agent, Runner
from agents.mcp import MCPServerStreamableHttp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tasks_agent")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Inside the cluster, the MCP server is reachable via its K8s service name.
# No port-forward needed — pod-to-pod networking handles it.
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://mcp-server:8001/mcp")

# System instructions for the LLM.
# The agent discovers tool schemas from MCP automatically, but these
# instructions give the LLM context about how to use them.
AGENT_INSTRUCTIONS = """
You are a helpful task management assistant. You help users create,
view, update, and delete tasks using natural language.

You have access to these tools via MCP:
- create_task: Create a new task (requires title and description)
- list_tasks: List tasks, optionally filtered by status
- get_task: Get a specific task by its ID
- update_task: Update a task's title, description, or status
- delete_task: Delete a task by its ID

When a user asks to manage tasks, use the appropriate tool.
Always confirm what you did after performing an action.
If a user's request is ambiguous, ask for clarification.
"""


# ---------------------------------------------------------------------------
# Chainlit lifecycle hooks
# ---------------------------------------------------------------------------

@cl.on_chat_start
async def on_chat_start():
    """
    Fires when a user opens the chat in their browser.

    We connect to the MCP server here (once per session) and store
    the MCP connection + Agent in the user's session so subsequent
    messages can reuse them.
    """
    # Connect to the MCP server and discover tools
    mcp_server = MCPServerStreamableHttp(
        name="Tasks MCP Server",
        params={"url": MCP_SERVER_URL},
        cache_tools_list=True,
    )

    # Enter the async context manager to establish the connection
    await mcp_server.__aenter__()

    # Create the agent with MCP tools
    agent = Agent(
        name="Task Manager",
        instructions=AGENT_INSTRUCTIONS,
        mcp_servers=[mcp_server],
    )

    # Store in Chainlit's per-user session so @cl.on_message can use them
    cl.user_session.set("mcp_server", mcp_server)
    cl.user_session.set("agent", agent)

    logger.info(f"Session started — connected to MCP at {MCP_SERVER_URL}")

    await cl.Message(
        content=(
            "Hello! I'm your Task Manager assistant. "
            "I can help you create, view, update, and delete tasks. "
            "What would you like to do?"
        )
    ).send()


@cl.on_chat_end
async def on_chat_end():
    """
    Fires when the user closes the chat or disconnects.
    Clean up the MCP server connection.
    """
    mcp_server = cl.user_session.get("mcp_server")
    if mcp_server:
        await mcp_server.__aexit__(None, None, None)
        logger.info("Session ended — MCP connection closed")


@cl.on_message
async def on_message(message: cl.Message):
    """
    Fires on every user message.

    Flow:
    1. Get the agent from the session
    2. Pass the user's message to Runner.run()
    3. The Runner sends it to the OpenAI API with tool definitions
    4. If the LLM decides to call a tool, the SDK calls it on our MCP server
    5. The final answer comes back and we display it
    """
    agent = cl.user_session.get("agent")
    if not agent:
        await cl.Message(content="Session not initialized. Please refresh the page.").send()
        return

    # Show a thinking indicator while the agent works
    msg = cl.Message(content="")
    await msg.send()

    try:
        # Runner.run() handles the full cycle:
        #   user message → LLM → (optional tool calls to MCP) → final answer
        result = await Runner.run(agent, message.content)
        msg.content = result.final_output
        await msg.update()
    except Exception as e:
        logger.error(f"Agent error: {e}", exc_info=True)
        msg.content = f"Sorry, something went wrong: {e}"
        await msg.update()
