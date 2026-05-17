"""MCP tool: clear_notifications"""

import json

from pydantic import BaseModel, ConfigDict
from mcp.server.fastmcp import FastMCP

from auth_context import get_current_user
from services.notification_service import clear_notifications as svc_clear_notifications


class ClearNotificationsInput(BaseModel):
    """Input for clearing notifications (no parameters needed)."""

    model_config = ConfigDict(extra="forbid")


def register(mcp: FastMCP) -> None:
    """Register the clear_notifications tool on the given MCP server."""

    @mcp.tool(
        name="clear_notifications",
        annotations={
            "title": "Clear Notifications",
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def clear_notifications(params: ClearNotificationsInput) -> str:
        """Clear all notifications from the notification service.

        This permanently removes all stored notifications. Use this after
        the user has reviewed their notifications.

        Returns:
            str: JSON confirmation message.
        """
        try:
            user = get_current_user()
            message = await svc_clear_notifications(user_id=user.id)
            return json.dumps({"message": message})
        except Exception as e:
            return f"Error clearing notifications: {e}"
