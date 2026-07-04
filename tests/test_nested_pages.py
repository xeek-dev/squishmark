"""Tests for nested pages support: recursive listing and multi-segment slugs.

Covers the recursive ``list_directory`` paths (local ``rglob`` and the GitHub
git trees API) and the ``/{slug:path}`` page route serving pages from
subdirectories of ``pages/``.
"""

import json

import httpx
import pytest
from fastapi.testclient import TestClient

from squishmark.config import Settings
from squishmark.services.cache import Cache
from squishmark.services.github import GitHubService


@pytest.fixture
def local_service(tmp_path):
    """A GitHubService over a local content tree with nested pages."""
    (tmp_path / "pages" / "docs").mkdir(parents=True)
    (tmp_path / "pages" / "about.md").write_text("---\ntitle: About\n---\n", encoding="utf-8")
    (tmp_path / "pages" / "docs" / "setup.md").write_text("---\ntitle: Setup\n---\n", encoding="utf-8")
    (tmp_path / "pages" / "docs" / ".draft.md").write_text("hidden", encoding="utf-8")
    (tmp_path / "pages" / ".obsidian").mkdir()
    (tmp_path / "pages" / ".obsidian" / "workspace.md").write_text("hidden", encoding="utf-8")

    settings = Settings(github_content_repo=f"file://{tmp_path}")
    cache = Cache(ttl_seconds=300)
    return GitHubService(settings, cache)


@pytest.mark.asyncio
async def test_local_listing_recursive(local_service):
    files = await local_service.list_directory("pages", recursive=True)
    assert files == ["pages/about.md", "pages/docs/setup.md"]


@pytest.mark.asyncio
async def test_local_listing_recursive_skips_dotted_paths(local_service):
    files = await local_service.list_directory("pages", recursive=True)
    assert not any(".draft" in f or ".obsidian" in f for f in files)


@pytest.mark.asyncio
async def test_local_listing_non_recursive_unchanged(local_service):
    files = await local_service.list_directory("pages")
    assert files == ["pages/about.md"]


def _trees_transport(payload: dict, status_code: int = 200) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "/git/trees/main" in request.url.path
        assert request.url.params.get("recursive") == "1"
        return httpx.Response(status_code, content=json.dumps(payload))

    return httpx.MockTransport(handler)


def _github_service_with_transport(transport: httpx.MockTransport) -> GitHubService:
    settings = Settings(github_content_repo="owner/repo")
    service = GitHubService(settings, Cache(ttl_seconds=300))
    service._client = httpx.AsyncClient(transport=transport)
    return service


@pytest.mark.asyncio
async def test_github_listing_recursive_uses_trees_api():
    payload = {
        "tree": [
            {"path": "pages", "type": "tree"},
            {"path": "pages/about.md", "type": "blob"},
            {"path": "pages/docs", "type": "tree"},
            {"path": "pages/docs/setup.md", "type": "blob"},
            {"path": "posts/2026-01-01-hello.md", "type": "blob"},
            {"path": "config.yml", "type": "blob"},
        ],
        "truncated": False,
    }
    service = _github_service_with_transport(_trees_transport(payload))
    files = await service.list_directory("pages", recursive=True)
    assert files == ["pages/about.md", "pages/docs/setup.md"]
    await service.close()


@pytest.mark.asyncio
async def test_github_listing_recursive_missing_ref_returns_empty():
    service = _github_service_with_transport(_trees_transport({}, status_code=404))
    files = await service.list_directory("pages", recursive=True)
    assert files == []
    await service.close()


# --- Route integration -----------------------------------------------------


@pytest.mark.integration
def test_nested_page_renders(fake_github, client: TestClient) -> None:
    fake_github.files["pages/docs/setup.md"] = "---\ntitle: Setup Guide\n---\n\n# Setup Guide\n\nSteps.\n"
    resp = client.get("/docs/setup")
    assert resp.status_code == 200
    assert "Setup Guide" in resp.text


@pytest.mark.integration
def test_nested_page_unknown_404(client: TestClient) -> None:
    resp = client.get("/docs/no-such-page")
    assert resp.status_code == 404


@pytest.mark.integration
def test_dot_segments_rejected(client: TestClient) -> None:
    # Percent-encoded dot segments reach the route without client-side URL
    # normalization and must not be forwarded to the content store.
    resp = client.get("/docs/%2e%2e/secret")
    assert resp.status_code == 404


@pytest.mark.integration
def test_dotfile_page_rejected(client: TestClient) -> None:
    resp = client.get("/.well-known/anything")
    assert resp.status_code == 404


@pytest.mark.integration
def test_nested_page_in_sitemap(fake_github, client: TestClient) -> None:
    fake_github.files["pages/docs/setup.md"] = "---\ntitle: Setup Guide\n---\n\nSteps.\n"
    resp = client.get("/sitemap.xml")
    assert resp.status_code == 200
    assert "/docs/setup" in resp.text
