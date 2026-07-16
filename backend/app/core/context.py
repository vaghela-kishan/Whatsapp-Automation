"""Per-request context propagated via :mod:`contextvars`.

The request id is set by :class:`app.core.middleware.RequestContextMiddleware`
at the start of each request and read by the logging layer, so every log line
emitted while handling a request is automatically correlated.
"""

from __future__ import annotations

from contextvars import ContextVar, Token

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)


def bind_request_id(value: str) -> Token[str | None]:
    """Bind ``value`` as the current request id; returns a reset token."""
    return _request_id.set(value)


def reset_request_id(token: Token[str | None]) -> None:
    """Restore the request id to its previous value."""
    _request_id.reset(token)


def get_request_id() -> str | None:
    """Return the current request id, or ``None`` outside a request scope."""
    return _request_id.get()
