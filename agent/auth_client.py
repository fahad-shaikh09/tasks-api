"""Self-contained session validator for the agent.

Duplicates backend/app/core/auth.py because the agent's Docker build
context is only the agent/ directory — it can't reach backend/.
Keep these two implementations in sync.
"""

from __future__ import annotations

import os
import logging
from dataclasses import dataclass
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8003")
GET_SESSION_URL = f"{AUTH_SERVICE_URL}/api/auth/get-session"


@dataclass(frozen=True)
class AuthUser:
    id: str
    email: Optional[str] = None
    name: Optional[str] = None


async def validate_session(cookie_header: str | None) -> AuthUser | None:
    """Validate a Cookie header against the auth-service."""
    if not cookie_header:
        return None
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(
                GET_SESSION_URL, headers={"Cookie": cookie_header}
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
