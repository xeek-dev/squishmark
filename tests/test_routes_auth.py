"""Integration tests for the GitHub OAuth auth routes.

Covers /auth/login (redirect to GitHub, unconfigured OAuth, dev bypass),
/auth/callback error handling (error param, missing code, bad state),
/auth/logout session clearing, and /auth/me. The token-exchange happy path is
not exercised here because it requires mocking GitHub's token/user endpoints.
"""

from typing import Any, Callable
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient

from squishmark.config import get_settings

pytestmark = pytest.mark.integration

# Matches SECRET_KEY pinned by the autouse conftest fixture.
VALID_STATE = "test-secret-key"[:16]


@pytest.fixture
def oauth_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Configure GitHub OAuth client credentials before the client fixture
    builds the app (settings are cached at first access)."""
    monkeypatch.setenv("GITHUB_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "test-client-secret")
    get_settings.cache_clear()


@pytest.fixture
def no_oauth_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure OAuth is unconfigured even if the developer's shell has it set."""
    monkeypatch.delenv("GITHUB_CLIENT_ID", raising=False)
    monkeypatch.delenv("GITHUB_CLIENT_SECRET", raising=False)
    get_settings.cache_clear()


# --- /auth/login --------------------------------------------------------------


def test_login_redirects_to_github_with_client_id(oauth_env: None, client: TestClient) -> None:
    resp = client.get("/auth/login", follow_redirects=False)
    assert resp.status_code == 307

    location = resp.headers["location"]
    parsed = urlparse(location)
    assert f"{parsed.scheme}://{parsed.netloc}{parsed.path}" == "https://github.com/login/oauth/authorize"

    params = parse_qs(parsed.query)
    assert params["client_id"] == ["test-client-id"]
    assert params["scope"] == ["read:user"]
    assert params["state"] == [VALID_STATE]
    assert params["redirect_uri"][0].endswith("/auth/callback")


def test_login_unconfigured_oauth_500(no_oauth_env: None, client: TestClient) -> None:
    resp = client.get("/auth/login", follow_redirects=False)
    assert resp.status_code == 500
    assert "GITHUB_CLIENT_ID" in resp.json()["detail"]


def test_login_dev_bypass_redirects_to_admin(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    """With DEBUG and DEV_SKIP_AUTH both on, login short-circuits to /admin."""
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("DEV_SKIP_AUTH", "true")
    get_settings.cache_clear()

    resp = client.get("/auth/login", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == "/admin"


# --- /auth/callback -------------------------------------------------------------


def test_callback_with_error_param_400(client: TestClient) -> None:
    resp = client.get("/auth/callback", params={"error": "access_denied"})
    assert resp.status_code == 400
    assert "access_denied" in resp.json()["detail"]


def test_callback_missing_code_400(client: TestClient) -> None:
    resp = client.get("/auth/callback", params={"state": VALID_STATE})
    assert resp.status_code == 400
    assert "code" in resp.json()["detail"].lower()


def test_callback_bad_state_400(client: TestClient) -> None:
    """A wrong state parameter is rejected before any token exchange."""
    resp = client.get("/auth/callback", params={"code": "some-code", "state": "wrong-state"})
    assert resp.status_code == 400
    assert "state" in resp.json()["detail"].lower()


# --- /auth/logout ----------------------------------------------------------------


def test_logout_clears_session_and_redirects(
    seeded_client: Callable[[dict[str, Any]], TestClient],
) -> None:
    logged_in = seeded_client({"user": {"login": "admin-user"}})
    assert logged_in.get("/auth/me").status_code == 200

    resp = logged_in.get("/auth/logout", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == "/"

    # Session is gone: /auth/me is anonymous again.
    assert logged_in.get("/auth/me").status_code == 401


def test_logout_anonymous_still_redirects(client: TestClient) -> None:
    resp = client.get("/auth/logout", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == "/"


# --- /auth/me ---------------------------------------------------------------------


def test_me_anonymous_401(client: TestClient) -> None:
    resp = client.get("/auth/me")
    assert resp.status_code == 401


def test_me_returns_session_user(
    seeded_client: Callable[[dict[str, Any]], TestClient],
) -> None:
    user = {"login": "someone", "name": "Some One", "avatar_url": "https://example.com/a.png"}
    logged_in = seeded_client({"user": user})
    resp = logged_in.get("/auth/me")
    assert resp.status_code == 200
    assert resp.json() == user
