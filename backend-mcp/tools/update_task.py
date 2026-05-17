"""MCP tool: update_task"""

import json
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict
from mcp.server.fastmcp import FastMCP

from app.core.database import get_session
from services.task_service import update_task as svc_update_task


class UpdateTaskInput(BaseModel):
    """Input for updating an existing task. Only provided fields are changed."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    task_id: int = Field(
        ...,
        description="The ID of the task to update",
        ge=1,
    )
    title: Optional[str] = Field(
        default=None,
        description="New title for the task",
        min_length=1,
        max_length=200,
    )
    description: Optional[str] = Field(
        default=None,
        description="New description for the task",
        min_length=1,
    )
    status: Optional[str] = Field(
        default=None,
        description="New status (e.g., 'pending', 'in_progress', 'completed')",
        max_length=50,
    )


def register(mcp: FastMCP) -> None:
    """Register the update_task tool on the given MCP server."""

    @mcp.tool(
        name="update_task",
        annotations={
            "title": "Update Task",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def update_task(params: UpdateTaskInput) -> str:
        """Update an existing task's title, description, or status.

        Only the fields you provide will be changed; omitted fields stay as-is.
        Publishes a 'task-updated' event to Kafka via Dapr after a successful update.

        Args:
            params (UpdateTaskInput): Validated input containing:
                - task_id (int): ID of the task to update
                - title (Optional[str]): New title
                - description (Optional[str]): New description
                - status (Optional[str]): New status

        Returns:
            str: JSON object with the updated task, or an error if not found.
        """
        session = next(get_session())
        try:
            task = await svc_update_task(
                session=session,
                task_id=params.task_id,
                title=params.title,
                description=params.description,
                status=params.status,
            )
            if not task:
                return f"Error: Task with ID {params.task_id} not found."
            return json.dumps(task.model_dump(), indent=2, default=str)
        except Exception as e:
            return f"Error updating task: {e}"
        finally:
            session.close()
