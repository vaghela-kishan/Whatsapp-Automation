"""Shared, cross-module Pydantic schemas.

These define reusable API contracts (generic pagination, the error envelope,
simple message responses) so individual modules stay DRY and consistent.
"""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Message(BaseModel):
    """A minimal ``{"message": "..."}`` response."""

    message: str


class HealthResponse(BaseModel):
    """Payload returned by the health-check endpoint."""

    status: str = Field(examples=["ok"])
    version: str
    environment: str
    database: str = Field(examples=["up"])


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list = Field(default_factory=list)


class ErrorEnvelope(BaseModel):
    """Documents the standard error shape in the OpenAPI schema."""

    error: ErrorBody
    request_id: str | None = None


class PaginationParams(BaseModel):
    """Standard pagination query parameters."""

    page: int = Field(default=1, ge=1, description="1-based page number")
    size: int = Field(default=20, ge=1, le=100, description="Items per page (max 100)")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size


class Page(BaseModel, Generic[T]):
    """A paginated result envelope."""

    items: list[T]
    total: int
    page: int
    size: int
    pages: int

    @classmethod
    def create(cls, items: list[T], total: int, page: int, size: int) -> Page[T]:
        pages = (total + size - 1) // size if size else 0
        return cls(items=items, total=total, page=page, size=size, pages=pages)
