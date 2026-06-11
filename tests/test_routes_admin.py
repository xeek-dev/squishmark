"""Integration tests for admin auth gating and cache refresh.

Exercises the full dependency chain (``get_current_admin`` + ``verify_csrf_token``)
through the real app, covering the 401/403/200 auth ladder and CSRF enforcement
on ``POST /admin/cache/refresh``.
"""

from typing import Any, Callable

from fastapi.testclient import TestClient


def test_admin_dashboard_401_anonymous(client: TestClient) -> None:
    resp = client.get("/admin")
    assert resp.status_code == 401


def test_admin_dashboard_403_wrong_user(
    seeded_client: Callable[[dict[str, Any]], TestClient],
) -> None:
    """A logged-in user who is not in ADMIN_USERS gets 403, not 401."""
    wrong = seeded_client({"user": {"login": "not-an-admin"}})
    resp = wrong.get("/admin")
    assert resp.status_code == 403


def test_admin_dashboard_200_admin(admin_client: TestClient) -> None:
    resp = admin_client.get("/admin")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")


def test_cache_refresh_admin_with_csrf_succeeds(
    admin_client: TestClient,
    csrf_token: Callable[[TestClient], str],
) -> None:
    token = csrf_token(admin_client)
    resp = admin_client.post("/admin/cache/refresh", headers={"X-CSRF-Token": token})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "ok"
    assert set(body) == {"status", "cleared", "warmed", "duration_ms"}
    assert isinstance(body["cleared"], int)
    assert isinstance(body["warmed"], int)
    assert isinstance(body["duration_ms"], (int, float))


def test_cache_refresh_without_csrf_token_403(admin_client: TestClient) -> None:
    """Authenticated admin omitting the CSRF token is rejected by
    ``verify_csrf_token`` with 403."""
    resp = admin_client.post("/admin/cache/refresh")
    assert resp.status_code == 403


def test_cache_refresh_anonymous_401(client: TestClient) -> None:
    """Anonymous caller hits the auth dependency (401) before CSRF (403)."""
    resp = client.post("/admin/cache/refresh")
    assert resp.status_code == 401
