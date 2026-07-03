"""Integration tests for the public utility endpoints.

Covers /health, the / -> /posts redirect, the Atom feed, sitemap.xml,
robots.txt, favicon, and static serving (user + theme), all driven through the
real ``create_app()`` with the in-memory ``FakeGitHubService`` content from
``conftest.py`` (five published posts, one draft, a public and a hidden page,
one PNG favicon). The feed/sitemap/robots builders already have direct
handler-level unit tests in ``test_feed.py`` / ``test_seo.py``; these tests
exercise the routes end to end instead.
"""

import pytest
from fastapi.testclient import TestClient

from tests.conftest import FakeGitHubService

pytestmark = pytest.mark.integration


# --- /health and / ----------------------------------------------------------


def test_health_returns_healthy(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "healthy"}


def test_root_redirects_to_posts(client: TestClient) -> None:
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == "/posts"


# --- /feed.xml ---------------------------------------------------------------


def test_feed_content_type_and_entries(client: TestClient) -> None:
    resp = client.get("/feed.xml")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/atom+xml")
    # All five published posts fit within the 20-entry limit.
    for title in ("Post One", "Post Two", "Post Three", "Post Four", "Post Five"):
        assert title in resp.text


def test_feed_excludes_drafts(client: TestClient) -> None:
    resp = client.get("/feed.xml")
    assert resp.status_code == 200
    assert "Secret Draft" not in resp.text


# --- /sitemap.xml and /robots.txt --------------------------------------------


def test_sitemap_lists_posts_and_public_pages(client: TestClient) -> None:
    resp = client.get("/sitemap.xml")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/xml")
    assert "https://test.example.com/posts" in resp.text
    assert "https://test.example.com/posts/post-five" in resp.text
    assert "https://test.example.com/about" in resp.text


def test_sitemap_excludes_hidden_pages_and_drafts(client: TestClient) -> None:
    resp = client.get("/sitemap.xml")
    assert resp.status_code == 200
    assert "https://test.example.com/secret" not in resp.text
    assert "secret-draft" not in resp.text


def test_robots_txt(client: TestClient) -> None:
    resp = client.get("/robots.txt")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/plain")
    assert "User-agent: *" in resp.text
    assert "Disallow: /admin/*" in resp.text
    assert "Sitemap: https://test.example.com/sitemap.xml" in resp.text


# --- /favicon.ico -------------------------------------------------------------


def test_favicon_served_from_content_repo(client: TestClient) -> None:
    """The fake content only has static/favicon.png; the route falls through
    its preference list (.ico first) and serves it."""
    resp = client.get("/favicon.ico")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert resp.headers["cache-control"] == "public, max-age=86400"
    assert resp.content.startswith(b"\x89PNG")


def test_favicon_missing_404(fake_github: FakeGitHubService, client: TestClient) -> None:
    fake_github.binary_files.clear()
    resp = client.get("/favicon.ico")
    assert resp.status_code == 404


# --- /static/user/* ------------------------------------------------------------


def test_user_static_allowed_extension_served(client: TestClient) -> None:
    resp = client.get("/static/user/favicon.png")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert resp.headers["cache-control"] == "public, max-age=86400"


def test_user_static_disallowed_extension_404(fake_github: FakeGitHubService, client: TestClient) -> None:
    """A .txt file 404s even when it exists in the content repo, proving the
    extension allowlist is checked before the file lookup."""
    fake_github.binary_files["static/notes.txt"] = b"not servable"
    resp = client.get("/static/user/notes.txt")
    assert resp.status_code == 404


def test_user_static_missing_file_404(client: TestClient) -> None:
    resp = client.get("/static/user/missing.png")
    assert resp.status_code == 404


# --- /static/{theme}/* ----------------------------------------------------------


def test_theme_static_serves_real_file(client: TestClient) -> None:
    resp = client.get("/static/default/style.css")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/css")
    assert resp.headers["cache-control"] == "public, max-age=86400"


def test_theme_static_unknown_theme_falls_back_to_default(client: TestClient) -> None:
    """A theme dir that doesn't exist falls back to the default theme's file."""
    resp = client.get("/static/no-such-theme/style.css")
    assert resp.status_code == 200
    default = client.get("/static/default/style.css")
    assert resp.content == default.content


def test_theme_static_invalid_theme_name_400(client: TestClient) -> None:
    resp = client.get("/static/bad!theme/style.css")
    assert resp.status_code == 400


@pytest.mark.parametrize(
    "url_path",
    [
        "/static/default/..%2f..%2fconfig.yml",
        "/static/default/%2fabsolute.css",
    ],
)
def test_theme_static_rejects_path_traversal(client: TestClient, url_path: str) -> None:
    resp = client.get(url_path)
    assert resp.status_code == 400


def test_theme_static_missing_file_404(client: TestClient) -> None:
    resp = client.get("/static/default/does-not-exist.css")
    assert resp.status_code == 404
