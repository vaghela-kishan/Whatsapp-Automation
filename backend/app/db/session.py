"""Database engine, session factory, and the ``get_db`` dependency.

The engine is configured differently for SQLite (single-file dev database) and
PostgreSQL (pooled production database), selected purely from ``DATABASE_URL``.
"""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

_connect_args: dict[str, object] = (
    {"check_same_thread": False} if settings.is_sqlite else {}
)

_engine_kwargs: dict[str, object] = {
    "pool_pre_ping": True,
    "echo": settings.SQL_ECHO,
    "connect_args": _connect_args,
}
if not settings.is_sqlite:
    # Connection pooling tuned for a pooled Postgres deployment.
    _engine_kwargs.update({"pool_size": 10, "max_overflow": 20, "pool_recycle": 1800})

engine: Engine = create_engine(settings.DATABASE_URL, **_engine_kwargs)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


if settings.is_sqlite:

    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
        """SQLite ignores foreign keys unless explicitly enabled per-connection."""
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a request-scoped database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
