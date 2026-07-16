"""Authentication primitives — self-contained HS256 JWTs, no extra deps.

The admin dashboard is protected by a single set of credentials configured via
``ADMIN_USERNAME`` / ``ADMIN_PASSWORD`` in the environment. On a successful
login we mint a short-lived signed JWT; every protected endpoint then requires
that token (see ``app.api.deps.get_current_admin``).

We sign/verify the token by hand with the standard library (``hmac`` + SHA-256)
so the app needs no PyJWT/passlib install — one fewer thing to break on a fresh
machine — while still producing a standard, interoperable JWT.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

from app.core.config import settings


def _b64url_encode(data: bytes) -> str:
    """URL-safe base64 without padding (JWT convention)."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(segment: str) -> bytes:
    padding = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + padding)


def _sign(signing_input: bytes) -> bytes:
    return hmac.new(settings.SECRET_KEY.encode(), signing_input, hashlib.sha256).digest()


def create_access_token(subject: str, *, expires_minutes: int | None = None) -> str:
    """Return a signed HS256 JWT identifying ``subject`` (the admin username)."""
    minutes = expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"sub": subject, "role": "admin", "iat": now, "exp": now + minutes * 60}
    segments = [
        _b64url_encode(json.dumps(header, separators=(",", ":")).encode()),
        _b64url_encode(json.dumps(payload, separators=(",", ":")).encode()),
    ]
    signing_input = ".".join(segments).encode()
    segments.append(_b64url_encode(_sign(signing_input)))
    return ".".join(segments)


def decode_access_token(token: str) -> dict | None:
    """Validate signature + expiry. Returns the payload dict, or ``None``."""
    try:
        header_b64, payload_b64, sig_b64 = token.split(".")
    except ValueError:
        return None
    signing_input = f"{header_b64}.{payload_b64}".encode()
    try:
        provided = _b64url_decode(sig_b64)
    except (ValueError, TypeError):
        return None
    # Constant-time compare so a forged signature can't be timed out byte by byte.
    if not hmac.compare_digest(_sign(signing_input), provided):
        return None
    try:
        payload = json.loads(_b64url_decode(payload_b64))
    except (ValueError, TypeError):
        return None
    if int(payload.get("exp", 0)) < int(time.time()):
        return None  # expired
    return payload


def verify_admin_credentials(username: str, password: str) -> bool:
    """Constant-time check of a login attempt against the configured admin."""
    if not settings.ADMIN_USERNAME or not settings.ADMIN_PASSWORD:
        return False
    # Compare both fields with compare_digest to avoid leaking which one is wrong.
    user_ok = hmac.compare_digest(username, settings.ADMIN_USERNAME)
    pass_ok = hmac.compare_digest(password, settings.ADMIN_PASSWORD)
    return user_ok and pass_ok
