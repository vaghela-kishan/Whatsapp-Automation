"""Portable column types that behave correctly on both PostgreSQL and SQLite.

``GUID`` stores values as native ``UUID`` on PostgreSQL and as ``CHAR(36)`` on
SQLite, while always exposing a Python :class:`uuid.UUID` to the application.
This is the key to "develop on SQLite, deploy on Postgres".
"""

from __future__ import annotations

import uuid

from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.types import CHAR, TypeDecorator


class GUID(TypeDecorator):
    """Platform-independent UUID type."""

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PostgresUUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value: object, dialect: Dialect):
        if value is None:
            return None
        if not isinstance(value, uuid.UUID):
            value = uuid.UUID(str(value))
        if dialect.name == "postgresql":
            return value
        return str(value)

    def process_result_value(self, value: object, dialect: Dialect):
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))
