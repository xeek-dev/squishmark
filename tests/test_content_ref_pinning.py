"""Webhook pins content fetches to the pushed commit (issue #138).

Branch-path fetches from raw.githubusercontent.com go through a CDN that can
serve the pre-push file for minutes, so the webhook's cache warm could pin
stale content. Commit-SHA URLs are immutable, so the push handler pins the
service to the payload's ``after`` SHA for a bounded time.
"""

import hashlib
import hmac
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from squishmark.config import Settings
from squishmark.services.cache import Cache
from squishmark.services.github import GitHubService

SHA = "a" * 39 + "b"


# --- Unit: pin semantics -----------------------------------------------------


def _service() -> GitHubService:
    return GitHubService(Settings(github_content_repo="owner/repo"), Cache(ttl_seconds=300))


def test_content_ref_defaults_to_branch():
    assert _service().content_ref == "main"


def test_pin_takes_effect_and_expires(monkeypatch):
    service = _service()
    now = 1000.0
    monkeypatch.setattr("squishmark.services.github.time.monotonic", lambda: now)
    service.pin_content_ref(SHA, ttl_seconds=600)
    assert service.content_ref == SHA

    now = 1599.0
    assert service.content_ref == SHA
    now = 1601.0
    assert service.content_ref == "main"


@pytest.mark.asyncio
async def test_fetches_use_pinned_sha_in_urls():
    service = _service()
    service.pin_content_ref(SHA)
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(200, text="content")

    service._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    await service.get_file("posts/a.md", use_cache=False)
    assert seen and f"/owner/repo/{SHA}/posts/a.md" in seen[0]
    await service.close()


# --- Integration: webhook pins from the payload ------------------------------

pytestmark_integration = pytest.mark.integration

WEBHOOK_SECRET = "test-webhook-secret"  # matches the autouse fixture


def _signed_headers(body: bytes) -> dict[str, str]:
    digest = hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
    return {
        "X-Hub-Signature-256": f"sha256={digest}",
        "X-GitHub-Event": "push",
        "Content-Type": "application/json",
    }


@pytest.mark.integration
def test_push_pins_to_after_sha(fake_github, client: TestClient) -> None:
    body = json.dumps({"ref": "refs/heads/main", "after": SHA}).encode()
    resp = client.post("/webhooks/github", content=body, headers=_signed_headers(body))
    assert resp.status_code == 200, resp.text
    assert resp.json()["content_ref"] == SHA
    assert fake_github.pinned_refs == [SHA]


@pytest.mark.integration
def test_push_to_other_branch_does_not_pin(fake_github, client: TestClient) -> None:
    body = json.dumps({"ref": "refs/heads/feature", "after": SHA}).encode()
    resp = client.post("/webhooks/github", content=body, headers=_signed_headers(body))
    assert resp.status_code == 200
    assert resp.json()["content_ref"] == "main"
    assert fake_github.pinned_refs == []


@pytest.mark.integration
def test_branch_deletion_zero_sha_does_not_pin(fake_github, client: TestClient) -> None:
    body = json.dumps({"ref": "refs/heads/main", "after": "0" * 40}).encode()
    resp = client.post("/webhooks/github", content=body, headers=_signed_headers(body))
    assert resp.status_code == 200
    assert fake_github.pinned_refs == []


@pytest.mark.integration
def test_unparseable_payload_still_refreshes(fake_github, client: TestClient) -> None:
    body = b"not json"
    resp = client.post("/webhooks/github", content=body, headers=_signed_headers(body))
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    assert fake_github.pinned_refs == []
