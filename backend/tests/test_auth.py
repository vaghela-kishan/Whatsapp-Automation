"""Tests for admin authentication and route protection."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_login_rejects_bad_credentials(anon_client: TestClient) -> None:
    res = anon_client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "nope"}
    )
    assert res.status_code == 401


def test_login_issues_token_and_grants_access(anon_client: TestClient) -> None:
    res = anon_client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "admin123"}
    )
    assert res.status_code == 200
    token = res.json()["access_token"]
    assert token.count(".") == 2  # a well-formed JWT

    auth = {"Authorization": f"Bearer {token}"}
    assert anon_client.get("/api/v1/stats/dashboard", headers=auth).status_code == 200
    assert anon_client.get("/api/v1/auth/me", headers=auth).json()["username"] == "admin"


def test_protected_route_requires_token(anon_client: TestClient) -> None:
    assert anon_client.get("/api/v1/stats/dashboard").status_code == 401
    assert anon_client.get("/api/v1/orders").status_code == 401


def test_garbage_token_is_rejected(anon_client: TestClient) -> None:
    res = anon_client.get(
        "/api/v1/stats/dashboard", headers={"Authorization": "Bearer x.y.z"}
    )
    assert res.status_code == 401


def test_public_routes_need_no_token(anon_client: TestClient) -> None:
    assert anon_client.get("/api/v1/health").status_code == 200
    assert anon_client.get("/api/v1/system/info").status_code == 200
    # The customer message pipeline stays public (real traffic is Meta-signed).
    res = anon_client.post(
        "/api/v1/chat/send", json={"wa_id": "910000007777", "text": "hi"}
    )
    assert res.status_code == 201
