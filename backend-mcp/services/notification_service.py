"""
Notification Service Client

Calls the notification microservice's REST API to fetch and clear
notifications. The notification service runs in the same K8s namespace
and is reachable via its Service DNS name.

Flow:
    MCP tool → this client → HTTP GET/DELETE → notification service (port 8002)
"""

import os
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

NOTIFICATION_SERVICE_URL = os.getenv(
    "NOTIFICATION_SERVICE_URL", "http://notification:8002"
)


async def list_notifications(limit: Optional[int] = None) -> list[dict]:
    """
    Fetch notifications from the notification service (newest first).

    Args:
        limit: Max number of notifications to return. None = all.

    Returns:
        List of notification dicts, each with:
        {id, message, event_type, task_id, timestamp}
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{NOTIFICATION_SERVICE_URL}/notifications",
            timeout=10.0,
        )
        response.raise_for_status()
        notifications = response.json()

    if limit:
        notifications = notifications[:limit]

    return notifications


async def clear_notifications() -> str:
    """
    Clear all notifications from the notification service.

    Returns:
        Confirmation message from the service.
    """
    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"{NOTIFICATION_SERVICE_URL}/notifications",
            timeout=10.0,
        )
        response.raise_for_status()
        return response.json().get("message", "Notifications cleared")
