"""MCP tool: delete_task"""

import json

from pydantic import BaseModel, Field, ConfigDict
from mcp.server.fastmcp import FastMCP

from app.core.database import get_session
from auth_context import get_current_user
from services.task_service import delete_task as svc_delete_task


class DeleteTaskInput(BaseModel):
    """Input for deleting a task by ID."""

    model_config = ConfigDict(extra="forbid")

    task_id: int = Field(
        ...,
        description="The ID of the task to delete",
        ge=1,
    )


def register(mcp: FastMCP) -> None:
    """Register the delete_task tool on the given MCP server."""

    @mcp.tool(
        name="delete_task",
        annotations={
            "title": "Delete Task",
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def delete_task(params: DeleteTaskInput) -> str:
        """Delete a task from the system permanently.

        Removes the task from the database and publishes a 'task-deleted'
        event to Kafka via Dapr. This action cannot be undone.

        Args:
            params (DeleteTaskInput): Validated input containing:
                - task_id (int): ID of the task to delete

        Returns:
            str: JSON confirmation message, or an error if not found.
        """
        user = get_current_user()
        session = next(get_session())
        try:
            deleted = await svc_delete_task(
                session=session, user_id=user.id, task_id=params.task_id
            )
            if not deleted:
                return f"Error: Task with ID {params.task_id} not found."
            return json.dumps(
                {"message": f"Task {params.task_id} deleted successfully."}
            )
        except Exception as e:
            return f"Error deleting task: {e}"
        finally:
            session.close()
