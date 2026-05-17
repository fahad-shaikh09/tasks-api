"""
Shared session validator.

Calls the auth-service to verify a session cookie and return the
associated user. Used by every Python service (mcp-server, notification,
agent) so they all agree on identity.

Better-auth's /api/auth/get-session endpoint:
  GET {AUTH_SERVICE_URL}/api/auth/get-session
  - Reads cookie from the incoming request
  - Returns {"session": {...}, "user": {"id": "...", "email": "...", ...}}
  - Returns 401/empty body if no valid session
"""

from __future__ import annotations

import os
import logging
from dataclasses import dataclass
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# In-cluster URL of the auth-service.
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8003")
GET_SESSION_URL = f"{AUTH_SERVICE_URL}/api/auth/get-session"


@dataclass(frozen=True)
class AuthUser:
    """Minimal user info returned by the validator. Add fields as needed."""

    id: str
    email: Optional[str] = None
    name: Optional[str] = None


async def validate_session(cookie_header: str | None) -> AuthUser | None:
    """Validate a Cookie header against the auth-service.

    Args:
        cookie_header: Raw value of the incoming request's Cookie header.
            Pass through verbatim — better-auth picks the session cookie
            out of it by name.

    Returns:
        AuthUser if the session is valid, None otherwise. Never raises.
    """
    if not cookie_header:
        return None

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(
                GET_SESSION_URL,
                headers={"Cookie": cookie_header},
            )
    except Exception as e:  # noqa: BLE001
        logger.warning("validate_session: auth-service unreachable: %r", e)
        return None

    if r.status_code != 200:
        return None

    try:
        data = r.json()
    except Exception:  # noqa: BLE001
        return None

    # better-auth returns null/empty when there's no session
    if not data:
        return None

    user = data.get("user") if isinstance(data, dict) else None
    if not user or not user.get("id"):
        return None

    return AuthUser(
        id=str(user["id"]),
        email=user.get("email"),
        name=user.get("name"),
    )
