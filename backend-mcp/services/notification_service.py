"""
Notification Service Client

Calls the notification microservice's REST API to fetch and clear the
current user's notifications. Filters by user_id so each call only
returns what the authenticated user is allowed to see.
"""

import os
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

NOTIFICATION_SERVICE_URL = os.getenv(
    "NOTIFICATION_SERVICE_URL", "http://notification:8002"
)


async def list_notifications(user_id: str, limit: Optional[int] = None) -> list[dict]:
    """Fetch the given user's notifications, newest first."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{NOTIFICATION_SERVICE_URL}/notifications",
            params={"user_id": user_id},
            timeout=10.0,
        )
        response.raise_for_status()
        notifications = response.json()

    if limit:
        notifications = notifications[:limit]

    return notifications


async def clear_notifications(user_id: str) -> str:
    """Clear the given user's notifications."""
    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"{NOTIFICATION_SERVICE_URL}/notifications",
            params={"user_id": user_id},
            timeout=10.0,
        )
        response.raise_for_status()
        return response.json().get("message", "Notifications cleared")
