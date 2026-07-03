"""Integration tests for the /archive route."""

import pytest
from fastapi.testclient import TestClient

from tests.conftest import FakeGitHubService

pytestmark = pytest.mark.integration


def _body(title: str, *, date: str | None = None, draft: bool = False) -> str:
    date_line = f"date: {date}\n" if date else ""
    draft_line = "draft: true\n" if draft else ""
    return f"---\ntitle: {title}\n{date_line}{draft_line}---\n\n# {title}\n\nBody.\n"


def _install(fake_github: FakeGitHubService) -> None:
    fake_github.files = {
        "posts/2026-01-15-hello.md": _body("Hello World", date="2026-01-15"),
        "posts/2025-12-31-review.md": _body("Year Review", date="2025-12-31"),
        "posts/undated.md": _body("Timeless"),
        "posts/2026-02-01-secret.md": _body("Secret Draft", date="2026-02-01", draft=True),
    }


def test_archive_groups_by_year_and_month(fake_github: FakeGitHubService, client: TestClient) -> None:
    _install(fake_github)
    resp = client.get("/archive")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")
    assert "2026" in resp.text
    assert "2025" in resp.text
    assert "January" in resp.text
    assert "December" in resp.text
    assert "Hello World" in resp.text
    assert "Year Review" in resp.text


def test_archive_includes_undated_group(fake_github: FakeGitHubService, client: TestClient) -> None:
    _install(fake_github)
    resp = client.get("/archive")
    assert resp.status_code == 200
    assert "Undated" in resp.text
    assert "Timeless" in resp.text


def test_archive_excludes_drafts_for_anon(fake_github: FakeGitHubService, client: TestClient) -> None:
    _install(fake_github)
    resp = client.get("/archive")
    assert resp.status_code == 200
    assert "Secret Draft" not in resp.text


def test_archive_includes_drafts_for_admin(fake_github: FakeGitHubService, admin_client: TestClient) -> None:
    _install(fake_github)
    resp = admin_client.get("/archive")
    assert resp.status_code == 200
    assert "Secret Draft" in resp.text
