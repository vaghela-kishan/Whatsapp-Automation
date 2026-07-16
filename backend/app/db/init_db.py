"""Database bootstrap for development/demo.

Creates all tables (via ``Base.metadata``) and seeds demo data when the DB is
empty. In production you'd run Alembic migrations instead — this convenience
path is gated behind ``SEED_ON_STARTUP`` and is safe to leave on for the demo.
"""

from __future__ import annotations

import logging

import app.models  # noqa: F401 — register every table on Base.metadata
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.services.seed import seed_if_empty, sync_faqs

logger = logging.getLogger("app.db.init")


def init_db() -> None:
    """Create tables if missing, seed demo data on an empty DB, and keep the
    FAQ catalog in sync (adds new FAQs to existing databases without a reseed)."""
    Base.metadata.create_all(bind=engine)
    logger.info("tables_ready")

    db = SessionLocal()
    try:
        seeded = seed_if_empty(db)
        if seeded:
            logger.info("demo_data_seeded")
        # Always reconcile the FAQ catalog (idempotent) so new order FAQs land
        # even when the database was seeded by an earlier version.
        sync_faqs(db)
    finally:
        db.close()
