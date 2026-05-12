#!/usr/bin/env python3
"""
Tasks MCP Server

An MCP server that exposes task management capabilities as tools
consumable by AI agents. It reuses the existing backend's models,
database layer, config, and Dapr/Kafka event publishing — no logic
is duplicated.

Usage (stdio, for local agent integration):
    python server.py

Usage (HTTP, for remote/multi-client access):
    python server.py --transport streamable-http --port 8001
"""

import sys
import logging
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup — two modes:
#
# LOCAL DEV: server.py lives in backend-mcp/, needs to reach backend/app/.
#   backend-mcp/  ← _mcp_dir   (added for services.*, tools.*)
#   backend/      ← _backend_dir (added for app.models, app.core, app.events)
#
# CONTAINER: everything is flat in /app (WORKDIR), no extra paths needed.
# ---------------------------------------------------------------------------
_mcp_dir = Path(__file__).resolve().parent
_backend_dir = _mcp_dir.parent / "backend"

if str(_mcp_dir) not in sys.path:
    sys.path.insert(0, str(_mcp_dir))

# Only add backend path in local dev (directory exists as a sibling)
if _backend_dir.is_dir() and str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

# ---------------------------------------------------------------------------
# Now we can safely import backend modules and our own tools/services
# ---------------------------------------------------------------------------
from mcp.server.fastmcp import FastMCP  # noqa: E402
from app.core.database import create_db_and_tables  # noqa: E402
from tools import create_task, list_tasks, get_task, update_task, delete_task  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("tasks_mcp")

# ---------------------------------------------------------------------------
# Parse args early so we can pass host/port to the FastMCP constructor.
# (FastMCP binds host/port at init time, not at .run() time.)
# ---------------------------------------------------------------------------
import argparse

parser = argparse.ArgumentParser(description="Tasks MCP Server")
parser.add_argument(
    "--transport",
    choices=["stdio", "streamable-http"],
    default="stdio",
    help="Transport mechanism (default: stdio for local agent use)",
)
parser.add_argument(
    "--host",
    default="0.0.0.0",
    help="Bind address for HTTP transport (default: 0.0.0.0)",
)
parser.add_argument(
    "--port",
    type=int,
    default=8001,
    help="Port for HTTP transport (default: 8001)",
)
args = parser.parse_args()

# ---------------------------------------------------------------------------
# Initialize the MCP server
# ---------------------------------------------------------------------------
mcp = FastMCP("tasks_mcp", host=args.host, port=args.port)

# ---------------------------------------------------------------------------
# Register all tools
# Each tool module exposes a register(mcp) function that adds its tool.
# ---------------------------------------------------------------------------
create_task.register(mcp)
list_tasks.register(mcp)
get_task.register(mcp)
update_task.register(mcp)
delete_task.register(mcp)

logger.info("All MCP tools registered: create_task, list_tasks, get_task, update_task, delete_task")

# ---------------------------------------------------------------------------
# Ensure database tables exist (same as backend's startup hook)
# ---------------------------------------------------------------------------
create_db_and_tables()
logger.info("Database tables verified/created")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logger.info(f"Starting tasks_mcp — transport={args.transport}, host={args.host}, port={args.port}")
    mcp.run(transport=args.transport)
