"""Custom ASGI middleware.

``RequestContextMiddleware`` gives every request a correlation id, binds it to
the logging context, measures wall-clock latency, and echoes both back on the
response headers (``X-Request-ID``, ``X-Process-Time-ms``).
"""

from __future__ import annotations

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.context import bind_request_id, reset_request_id

logger = logging.getLogger("app.request")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        token = bind_request_id(request_id)
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.exception(
                "request_failed method=%s path=%s elapsed_ms=%.2f",
                request.method,
                request.url.path,
                elapsed_ms,
            )
            raise
        else:
            elapsed_ms = (time.perf_counter() - start) * 1000
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time-ms"] = f"{elapsed_ms:.2f}"
            logger.info(
                "request_completed method=%s path=%s status=%s elapsed_ms=%.2f",
                request.method,
                request.url.path,
                response.status_code,
                elapsed_ms,
            )
            return response
        finally:
            reset_request_id(token)
