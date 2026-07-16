"""Admin authentication endpoints.

``POST /auth/login`` exchanges the configured admin username/password for a
signed JWT. ``GET /auth/me`` lets the frontend confirm a stored token is still
valid on page load. Every other admin/data router requires the resulting token.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from app.api.deps import get_current_admin
from app.core.config import settings
from app.core.exceptions import UnauthorizedError
from app.core.security import create_access_token, verify_admin_credentials
from app.schemas.auth import AdminInfo, LoginRequest, TokenResponse

logger = logging.getLogger("app.auth")

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=TokenResponse, summary="Admin login")
def login(payload: LoginRequest) -> TokenResponse:
    if not verify_admin_credentials(payload.username, payload.password):
        logger.warning("login_failed username=%s", payload.username)
        raise UnauthorizedError("Incorrect username or password.")
    token = create_access_token(payload.username)
    logger.info("login_ok username=%s", payload.username)
    return TokenResponse(
        access_token=token,
        username=payload.username,
        expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    )


@router.get("/me", response_model=AdminInfo, summary="Current admin (token check)")
def me(username: str = Depends(get_current_admin)) -> AdminInfo:
    return AdminInfo(username=username)
