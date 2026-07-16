"""Pytest fixtures.

Tests run against an isolated in-memory SQLite database (shared across the
connection pool via ``StaticPool``) and override the ``get_db`` dependency, so
they never touch the developer's ``dev.db`` file.
"""

from __future__ import annotations

import os

# Force offline providers for tests BEFORE app config is imported, so the suite
# never calls real Gemini / WhatsApp (or consumes API quota). Env vars take
# precedence over the .env file in pydantic-settings.
os.environ.setdefault("AI_PROVIDER", "mock")
os.environ["AI_PROVIDER"] = "mock"
os.environ["WHATSAPP_PROVIDER"] = "mock"
os.environ["SEED_ON_STARTUP"] = "false"

from collections.abc import Generator

import pytest
from app.api.deps import get_db
from app.db.base import Base
from app.main import app
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    bind=test_engine, autoflush=False, autocommit=False, expire_on_commit=False
)

# Create the schema for whatever models exist (none yet in Step 1).
Base.metadata.create_all(bind=test_engine)


def _override_get_db() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    """An authenticated admin client (the dashboard is always used signed-in)."""
    from app.core.security import create_access_token

    with TestClient(app) as test_client:
        token = create_access_token("admin")
        test_client.headers.update({"Authorization": f"Bearer {token}"})
        yield test_client


@pytest.fixture()
def anon_client() -> Generator[TestClient, None, None]:
    """A client with no auth token — for testing that guards reject access."""
    with TestClient(app) as test_client:
        yield test_client
