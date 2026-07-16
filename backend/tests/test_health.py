"""Smoke tests for the Step 1 foundation."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_root_returns_service_metadata(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["service"]
    assert body["docs"] == "/docs"


def test_health_reports_ok_and_db_up(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "up"
    # Tracing header must be present on every response.
    assert "X-Request-ID" in response.headers
    assert "X-Process-Time-ms" in response.headers


def test_unknown_route_uses_error_envelope(client: TestClient) -> None:
    response = client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "NOT_FOUND"
    assert "request_id" in body


def test_openapi_schema_is_served(client: TestClient) -> None:
    response = client.get("/api/v1/openapi.json")
    assert response.status_code == 200
    assert response.json()["info"]["title"]
