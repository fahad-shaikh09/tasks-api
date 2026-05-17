"""MCP tool: get_task"""

import json

from pydantic import BaseModel, Field, ConfigDict
from mcp.server.fastmcp import FastMCP

from app.core.database import get_session
from auth_context import get_current_user
from services.task_service import get_task as svc_get_task


class GetTaskInput(BaseModel):
    """Input for fetching a single task by ID."""

    model_config = ConfigDict(extra="forbid")

    task_id: int = Field(
        ...,
        description="The ID of the task to retrieve (e.g., 1, 42)",
        ge=1,
    )


def register(mcp: FastMCP) -> None:
    """Register the get_task tool on the given MCP server."""

    @mcp.tool(
        name="get_task",
        annotations={
            "title": "Get Task",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def get_task(params: GetTaskInput) -> str:
        """Fetch a single task by its ID.

        Args:
            params (GetTaskInput): Validated input containing:
                - task_id (int): The task's database ID

        Returns:
            str: JSON object with the task data, or an error message if not found.
        """
        user = get_current_user()
        session = next(get_session())
        try:
            task = svc_get_task(session=session, user_id=user.id, task_id=params.task_id)
            if not task:
                return f"Error: Task with ID {params.task_id} not found."
            return json.dumps(task.model_dump(), indent=2, default=str)
        except Exception as e:
            return f"Error fetching task: {e}"
        finally:
            session.close()
