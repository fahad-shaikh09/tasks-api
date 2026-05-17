"""MCP tool: list_notifications"""

import json
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict
from mcp.server.fastmcp import FastMCP

from auth_context import get_current_user
from services.notification_service import list_notifications as svc_list_notifications


class ListNotificationsInput(BaseModel):
    """Input for listing notifications."""

    model_config = ConfigDict(extra="forbid")

    limit: Optional[int] = Field(
        default=10,
        description="Maximum number of notifications to return (newest first)",
        ge=1,
        le=100,
    )


def register(mcp: FastMCP) -> None:
    """Register the list_notifications tool on the given MCP server."""

    @mcp.tool(
        name="list_notifications",
        annotations={
            "title": "List Notifications",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def list_notifications(params: ListNotificationsInput) -> str:
        """Fetch recent notifications from the notification service.

        Notifications are generated automatically when tasks are created,
        updated, or deleted. They flow through Kafka via Dapr and are
        stored by the notification microservice.

        Args:
            params (ListNotificationsInput): Validated input containing:
                - limit (Optional[int]): Max notifications to return (default 10)

        Returns:
            str: JSON object with notifications array:
                {
                    "count": int,
                    "notifications": [
                        {
                            "id": int,
                            "message": str,
                            "event_type": str,
                            "task_id": int,
                            "timestamp": str
                        }
                    ]
                }
        """
        try:
            user = get_current_user()
            notifications = await svc_list_notifications(
                user_id=user.id, limit=params.limit
            )
            response = {
                "count": len(notifications),
                "notifications": notifications,
            }
            return json.dumps(response, indent=2, default=str)
        except Exception as e:
            return f"Error fetching notifications: {e}"
