"""Declarative base for all ORM models.

A fixed naming convention is attached to the metadata so that every index,
unique/foreign-key/check constraint, and primary key gets a deterministic name.
This is required for reliable Alembic autogenerate and for SQLite's batch
("recreate table") migration strategy.
"""

from __future__ import annotations

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Base class every model inherits from."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)
