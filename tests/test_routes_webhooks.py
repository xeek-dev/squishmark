"""Integration tests for POST /webhooks/github.

Covers HMAC-SHA256 signature verification, the missing-signature and
invalid-signature paths, the non-push "ignored" response, and the
unconfigured-secret behaviour.
"""

import hashlib
import hmac

import pytest
from fastapi.testclient import TestClient

from squishmark.config import get_settings

pytestmark = pytest.mark.integration

WEBHOOK_SECRET = "test-webhook-secret"  # matches the autouse fixture


def _sign(body: bytes, secret: str = WEBHOOK_SECRET) -> str:
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def test_valid_push_returns_ok(client: TestClient) -> None:
    body = b'{"ref": "refs/heads/main"}'
    resp = client.post(
        "/webhooks/github",
        content=body,
        headers={
            "X-Hub-Signature-256": _sign(body),
            "X-GitHub-Event": "push",
            "Content-Type": "application/json",
        },
    )
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["status"] == "ok"
    assert "cleared" in payload
    assert "warmed" in payload


def test_invalid_signature_returns_401(client: TestClient) -> None:
    body = b'{"ref": "refs/heads/main"}'
    resp = client.post(
        "/webhooks/github",
        content=body,
        headers={
            "X-Hub-Signature-256": "sha256=deadbeef",
            "X-GitHub-Event": "push",
        },
    )
    assert resp.status_code == 401


def test_missing_signature_returns_401(client: TestClient) -> None:
    body = b'{"ref": "refs/heads/main"}'
    resp = client.post(
        "/webhooks/github",
        content=body,
        headers={"X-GitHub-Event": "push"},
    )
    assert resp.status_code == 401


def test_non_push_event_is_ignored(client: TestClient) -> None:
    """A correctly-signed non-push event short-circuits with an
    ``{"status": "ignored", "event": ...}`` response (webhooks.py:64-65)."""
    body = b'{"zen": "Keep it simple."}'
    resp = client.post(
        "/webhooks/github",
        content=body,
        headers={
            "X-Hub-Signature-256": _sign(body),
            "X-GitHub-Event": "ping",
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"status": "ignored", "event": "ping"}


def test_unconfigured_secret_returns_500(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With no webhook secret configured the route raises 500
    (webhooks.py:42-46). Override the env the autouse fixture set, then
    reload settings so the change takes effect for this request."""
    monkeypatch.delenv("GITHUB_WEBHOOK_SECRET", raising=False)
    get_settings.cache_clear()

    body = b'{"ref": "refs/heads/main"}'
    resp = client.post(
        "/webhooks/github",
        content=body,
        headers={
            "X-Hub-Signature-256": _sign(body),
            "X-GitHub-Event": "push",
        },
    )
    assert resp.status_code == 500
