"""Shared FastAPI dependencies.

Exposes the database-session dependency and the admin-auth guard so endpoints
depend on a single, stable import surface (``from app.api.deps import ...``).
"""

from __future__ import annotations

from fastapi import Header

from app.core.exceptions import UnauthorizedError
from app.core.security import decode_access_token
from app.db.session import get_db

__all__ = ["get_db", "get_current_admin"]


def get_current_admin(authorization: str | None = Header(default=None)) -> str:
    """Require a valid ``Authorization: Bearer <jwt>`` header.

    Returns the admin username on success; raises ``UnauthorizedError`` (401,
    rendered in the standard error envelope) otherwise. Attach to a router via
    ``dependencies=[Depends(get_current_admin)]`` to protect every route in it.
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise UnauthorizedError("Sign in to continue.")
    token = authorization.split(" ", 1)[1].strip()
    payload = decode_access_token(token)
    if payload is None:
        raise UnauthorizedError("Your session has expired — please sign in again.")
    return str(payload.get("sub", "admin"))
