"""Application exception hierarchy and global exception handlers.

Every error leaving the API uses one envelope::

    {
      "error": {"code": "NOT_FOUND", "message": "...", "details": [...]},
      "request_id": "..."
    }

Raise an :class:`AppException` subclass from services/CRUD; the registered
handlers translate it (and framework/uncaught errors) into that envelope.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.context import get_request_id

logger = logging.getLogger("app.error")


class AppException(Exception):
    """Base class for all expected, domain-level errors."""

    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"
    message: str = "An unexpected error occurred."

    def __init__(
        self,
        message: str | None = None,
        *,
        details: list[Any] | None = None,
        error_code: str | None = None,
        status_code: int | None = None,
    ) -> None:
        self.message = message or self.message
        self.details = details or []
        if error_code is not None:
            self.error_code = error_code
        if status_code is not None:
            self.status_code = status_code
        super().__init__(self.message)


class BadRequestError(AppException):
    status_code = 400
    error_code = "BAD_REQUEST"
    message = "The request could not be processed."


class UnauthorizedError(AppException):
    status_code = 401
    error_code = "UNAUTHORIZED"
    message = "Authentication is required."


class ForbiddenError(AppException):
    status_code = 403
    error_code = "FORBIDDEN"
    message = "You do not have permission to perform this action."


class NotFoundError(AppException):
    status_code = 404
    error_code = "NOT_FOUND"
    message = "The requested resource was not found."


class ConflictError(AppException):
    status_code = 409
    error_code = "CONFLICT"
    message = "The request conflicts with the current state of the resource."


class ValidationAppError(AppException):
    status_code = 422
    error_code = "VALIDATION_ERROR"
    message = "The submitted data is invalid."


_STATUS_CODE_MAP: dict[int, str] = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMITED",
    500: "INTERNAL_ERROR",
}


def _error_response(
    status_code: int,
    error_code: str,
    message: str,
    details: list[Any] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": error_code,
                "message": message,
                "details": details or [],
            },
            "request_id": get_request_id(),
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach all global exception handlers to the FastAPI app."""

    @app.exception_handler(AppException)
    async def _handle_app_exception(_: Request, exc: AppException) -> JSONResponse:
        if exc.status_code >= 500:
            logger.error(
                "app_exception code=%s message=%s",
                exc.error_code,
                exc.message,
                exc_info=exc,
            )
        return _error_response(exc.status_code, exc.error_code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def _handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {
                "loc": list(err.get("loc", [])),
                "msg": err.get("msg", ""),
                "type": err.get("type", ""),
            }
            for err in exc.errors()
        ]
        return _error_response(422, "VALIDATION_ERROR", "Request validation failed.", details)

    @app.exception_handler(StarletteHTTPException)
    async def _handle_http_exception(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        error_code = _STATUS_CODE_MAP.get(exc.status_code, "HTTP_ERROR")
        message = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        return _error_response(exc.status_code, error_code, message)

    @app.exception_handler(Exception)
    async def _handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_exception")
        # Never leak internals in production.
        message = (
            "Internal server error."
            if settings.is_production
            else f"{type(exc).__name__}: {exc}"
        )
        return _error_response(500, "INTERNAL_ERROR", message)
