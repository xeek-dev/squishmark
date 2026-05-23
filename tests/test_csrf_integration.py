"""Integration tests for CSRF enforcement on admin mutation routes.

These exercise the full FastAPI dependency chain via ``TestClient`` — unlike
``test_csrf.py`` (which calls ``verify_csrf_token`` directly) or
``test_admin_notes.py`` (which calls route handlers directly), the tests here
confirm that ``dependencies=[Depends(verify_csrf_token)]`` on the route
decorators actually fires, and in the correct order relative to auth.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.middleware.sessions import SessionMiddleware

from squishmark.models.db import get_db_session
from squishmark.routers.admin import router as admin_router
from squishmark.services.csrf import SESSION_KEY


def _app() -> FastAPI:
    """Minimal FastAPI app wired with admin router + SessionMiddleware."""
    app = FastAPI()
    app.add_middleware(SessionMiddleware, secret_key="test-secret-key", session_cookie="s")
    app.include_router(admin_router)
    # DB session dep — never reached by these tests, but FastAPI resolves all deps
    # eagerly so it has to return something.
    app.dependency_overrides[get_db_session] = lambda: AsyncMock()
    return app


@pytest.fixture
def settings_prod():
    """Patch settings to behave like production: debug off, dev_skip_auth off,
    'alice' is the only admin."""
    fake = MagicMock(
        debug=False,
        dev_skip_auth=False,
        admin_users_list=["alice"],
    )
    with (
        patch("squishmark.dependencies.get_settings", return_value=fake),
        patch("squishmark.services.csrf.get_settings", return_value=fake),
        patch("squishmark.routers.admin.get_settings", return_value=fake),
    ):
        yield fake


def _client_with_session(session_data: dict) -> TestClient:
    """Build a TestClient whose first request seeds ``request.session`` with
    ``session_data``. TestClient's cookie jar persists across requests, so once
    the session cookie is set, subsequent requests on the same client carry it.
    """
    app = _app()

    @app.get("/_test/seed-session")
    async def seed(request: Request) -> dict:
        for k, v in session_data.items():
            request.session[k] = v
        return {"ok": True}

    client = TestClient(app)
    resp = client.get("/_test/seed-session")
    assert resp.status_code == 200, resp.text
    return client


def test_unauthenticated_htmx_mutation_gets_401_redirect_not_403_csrf(settings_prod):
    """The crux of the dep-ordering fix: an unauthenticated HTMX POST must hit
    the auth check (401 + HX-Redirect), not CSRF (403)."""
    del settings_prod
    client = TestClient(_app())
    resp = client.post(
        "/admin/notes",
        json={"path": "/x", "text": "y"},
        headers={"HX-Request": "true"},
    )
    assert resp.status_code == 401
    assert resp.headers.get("HX-Redirect") == "/auth/login"


def test_authenticated_mutation_without_csrf_token_gets_403(settings_prod):
    """An admin who somehow omits the CSRF token is rejected."""
    del settings_prod
    client = _client_with_session({"user": {"login": "alice"}})
    resp = client.post(
        "/admin/notes",
        json={"path": "/x", "text": "y"},
    )
    assert resp.status_code == 403


def test_authenticated_mutation_with_stale_csrf_token_gets_403(settings_prod):
    """An admin sending a token that doesn't match the session value is rejected."""
    del settings_prod
    client = _client_with_session({"user": {"login": "alice"}, SESSION_KEY: "real-token"})
    resp = client.post(
        "/admin/notes",
        json={"path": "/x", "text": "y"},
        headers={"X-CSRF-Token": "stale-or-attacker-token"},
    )
    assert resp.status_code == 403


def test_get_admin_csrf_endpoint_returns_token_for_admin(settings_prod):
    """JSON callers can fetch the current token via GET /admin/csrf."""
    del settings_prod
    client = _client_with_session({"user": {"login": "alice"}})
    resp = client.get("/admin/csrf")
    assert resp.status_code == 200
    body = resp.json()
    assert "csrf_token" in body
    assert isinstance(body["csrf_token"], str)
    assert len(body["csrf_token"]) > 20


def test_get_admin_csrf_endpoint_is_auth_gated(settings_prod):
    """Unauthenticated callers must not be able to obtain a token."""
    del settings_prod
    client = TestClient(_app())
    resp = client.get("/admin/csrf")
    assert resp.status_code == 401
