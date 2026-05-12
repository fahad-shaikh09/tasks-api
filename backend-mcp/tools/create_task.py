"""MCP tool: create_task"""

import json
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict
from mcp.server.fastmcp import FastMCP

from app.core.database import get_session
from services.task_service import create_task as svc_create_task


class CreateTaskInput(BaseModel):
    """Input for creating a new task."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    title: str = Field(
        ...,
        description="Task title (e.g., 'Review Kubernetes logs')",
        min_length=1,
        max_length=200,
    )
    description: str = Field(
        ...,
        description="Detailed task description",
        min_length=1,
    )
    status: Optional[str] = Field(
        default=None,
        description="Initial task status. Defaults to 'pending' if omitted.",
        max_length=50,
    )


def register(mcp: FastMCP) -> None:
    """Register the create_task tool on the given MCP server."""

    @mcp.tool(
        name="create_task",
        annotations={
            "title": "Create Task",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": True,
        },
    )
    async def create_task(params: CreateTaskInput) -> str:
        """Create a new task in the task management system.

        Validates the input, stores the task in the database, and publishes
        a 'task-created' event to Kafka via Dapr so downstream services
        (e.g. notifications) can react.

        Args:
            params (CreateTaskInput): Validated input containing:
                - title (str): Task title
                - description (str): Task description
                - status (Optional[str]): Initial status, defaults to 'pending'

        Returns:
            str: JSON object with the created task including its assigned ID.
        """
        session = next(get_session())
        try:
            task = svc_create_task(
                session=session,
                title=params.title,
                description=params.description,
                status=params.status,
            )
            return json.dumps(task.model_dump(), indent=2, default=str)
        except Exception as e:
            return f"Error creating task: {e}"
        finally:
            session.close()
