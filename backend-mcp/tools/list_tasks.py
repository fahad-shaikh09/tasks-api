"""MCP tool: list_tasks"""

import json
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict
from mcp.server.fastmcp import FastMCP

from app.core.database import get_session
from services.task_service import list_tasks as svc_list_tasks


class ListTasksInput(BaseModel):
    """Input for listing tasks with optional filters and pagination."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    status: Optional[str] = Field(
        default=None,
        description="Filter by task status (e.g., 'pending', 'completed')",
        max_length=50,
    )
    limit: int = Field(
        default=20,
        description="Maximum number of tasks to return",
        ge=1,
        le=100,
    )
    offset: int = Field(
        default=0,
        description="Number of tasks to skip for pagination",
        ge=0,
    )


def register(mcp: FastMCP) -> None:
    """Register the list_tasks tool on the given MCP server."""

    @mcp.tool(
        name="list_tasks",
        annotations={
            "title": "List Tasks",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def list_tasks(params: ListTasksInput) -> str:
        """List tasks with optional filtering by status and pagination.

        Returns a paginated list of tasks. Use the offset parameter to
        page through large result sets.

        Args:
            params (ListTasksInput): Validated input containing:
                - status (Optional[str]): Filter by status
                - limit (int): Max results (1-100, default 20)
                - offset (int): Skip N results (default 0)

        Returns:
            str: JSON object with tasks array and pagination metadata:
                {
                    "total": int,
                    "count": int,
                    "offset": int,
                    "has_more": bool,
                    "next_offset": int | null,
                    "tasks": [{"id": int, "title": str, "description": str, "status": str}, ...]
                }
        """
        session = next(get_session())
        try:
            tasks, total = svc_list_tasks(
                session=session,
                status=params.status,
                limit=params.limit,
                offset=params.offset,
            )

            has_more = total > params.offset + len(tasks)
            response = {
                "total": total,
                "count": len(tasks),
                "offset": params.offset,
                "has_more": has_more,
                "next_offset": params.offset + len(tasks) if has_more else None,
                "tasks": [t.model_dump() for t in tasks],
            }
            return json.dumps(response, indent=2, default=str)
        except Exception as e:
            return f"Error listing tasks: {e}"
        finally:
            session.close()
