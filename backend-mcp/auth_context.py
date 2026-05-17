"""
Per-request user context for MCP tool handlers.

Why a contextvar instead of a parameter?
  FastMCP tool handlers receive only the tool's input schema — there's no
  hook to thread auth state through their signature. A contextvar set by
  the ASGI middleware (see middleware.py) is visible to whatever async
  code runs in that request, so each tool can pull the current user_id
  without changing tool signatures.
"""

from __future__ import annotations

from contextvars import ContextVar
from typing import Optional

from app.core.auth import AuthUser

current_user_var: ContextVar[Optional[AuthUser]] = ContextVar(
    "current_user", default=None
)


def get_current_user() -> AuthUser:
    """Return the user for the in-flight request, or raise if missing.

    The MCP auth middleware rejects unauthenticated requests with 401, so
    by the time a tool handler runs, current_user_var MUST be set. If it
    isn't, something is wired wrong — fail loudly rather than silently
    operating on no-user data.
    """
    user = current_user_var.get()
    if user is None:
        raise RuntimeError(
            "No authenticated user in context — auth middleware misconfigured?"
        )
    return user
