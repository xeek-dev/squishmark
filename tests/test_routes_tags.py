"""Integration tests for the /tags routes.

Driven through the real ``create_app()`` with the in-memory
``FakeGitHubService``. Tag content is installed per-test by replacing the
fake's files before the first request (the cached posts layer builds lazily).
"""

import pytest
from fastapi.testclient import TestClient

from tests.conftest import FakeGitHubService

pytestmark = pytest.mark.integration


def _tagged(title: str, tags: list[str], *, draft: bool = False) -> str:
    tag_line = "tags: [" + ", ".join(tags) + "]\n"
    draft_line = "draft: true\n" if draft else ""
    return f"---\ntitle: {title}\n{tag_line}{draft_line}---\n\n# {title}\n\nBody for {title}.\n"


def _install(fake_github: FakeGitHubService) -> None:
    fake_github.files = {
        "posts/2026-01-03-alpha.md": _tagged("Alpha", ["python", "cooking"]),
        "posts/2026-01-02-beta.md": _tagged("Beta", ["python"]),
        "posts/2026-01-01-gamma.md": _tagged("Gamma", ["aliens"]),
        "posts/2026-01-04-secret.md": _tagged("Secret Draft", ["hidden-tag"], draft=True),
    }


# --- /tags index -------------------------------------------------------------


def test_tags_index_lists_tags_with_counts(fake_github: FakeGitHubService, client: TestClient) -> None:
    _install(fake_github)
    resp = client.get("/tags")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")
    assert 'href="/tags/python"' in resp.text
    assert 'href="/tags/cooking"' in resp.text
    assert 'href="/tags/aliens"' in resp.text


def test_tags_index_excludes_draft_only_tag_for_anon(fake_github: FakeGitHubService, client: TestClient) -> None:
    _install(fake_github)
    resp = client.get("/tags")
    assert resp.status_code == 200
    assert "hidden-tag" not in resp.text


def test_tags_index_includes_draft_tag_for_admin(fake_github: FakeGitHubService, admin_client: TestClient) -> None:
    _install(fake_github)
    resp = admin_client.get("/tags")
    assert resp.status_code == 200
    assert "hidden-tag" in resp.text


# --- /tags/{tag} -------------------------------------------------------------


def test_tag_page_lists_matching_posts(fake_github: FakeGitHubService, client: TestClient) -> None:
    _install(fake_github)
    resp = client.get("/tags/python")
    assert resp.status_code == 200
    assert "Alpha" in resp.text
    assert "Beta" in resp.text
    assert "Gamma" not in resp.text


def test_tag_page_case_insensitive(fake_github: FakeGitHubService, client: TestClient) -> None:
    _install(fake_github)
    resp = client.get("/tags/PYTHON")
    assert resp.status_code == 200
    assert "Alpha" in resp.text
    assert "Beta" in resp.text


def test_unknown_tag_renders_empty_not_404(fake_github: FakeGitHubService, client: TestClient) -> None:
    _install(fake_github)
    resp = client.get("/tags/nonexistent")
    assert resp.status_code == 200
    assert "No posts" in resp.text


def test_tag_page_excludes_drafts_for_anon(fake_github: FakeGitHubService, client: TestClient) -> None:
    _install(fake_github)
    resp = client.get("/tags/hidden-tag")
    assert resp.status_code == 200
    assert "Secret Draft" not in resp.text


def test_tag_page_includes_drafts_for_admin(fake_github: FakeGitHubService, admin_client: TestClient) -> None:
    _install(fake_github)
    resp = admin_client.get("/tags/hidden-tag")
    assert resp.status_code == 200
    assert "Secret Draft" in resp.text
