"""Integration tests for the theme homepage at / (issue #32).

home.html is injected through the content-repo custom-template path
(``theme/home.html``), so no bundled theme ships one. The template must be
present before the lifespan loads custom templates, so these tests build their
own app rather than using the shared ``client`` fixture.
"""

from contextlib import contextmanager
from typing import Iterator

import pytest
from fastapi.testclient import TestClient

from squishmark.main import create_app
from tests.conftest import FakeGitHubService

pytestmark = pytest.mark.integration

# Renders the context contract home.html templates rely on, in a parseable form.
HOME_TEMPLATE = (
    "HOME"
    "|latest:{% for p in latest_posts %}{{ p.title }};{% endfor %}"
    "|featured:{% for p in featured_posts %}{{ p.title }};{% endfor %}"
    "|canonical:{{ canonical_url }}"
)


@contextmanager
def home_client(fake_github: FakeGitHubService, *, admin: bool = False) -> Iterator[TestClient]:
    """Yield a client whose content repo ships a home.html override."""
    fake_github.files["theme/home.html"] = HOME_TEMPLATE
    app = create_app()

    if admin:
        from fastapi import Request

        @app.get("/_test/seed-session")
        async def _seed(request: Request) -> dict:
            request.session["user"] = {"login": "admin-user"}
            return {"ok": True}

    base_url = "https://testserver" if admin else "http://testserver"
    with TestClient(app, base_url=base_url) as client:
        if admin:
            resp = client.get("/_test/seed-session")
            assert resp.status_code == 200, resp.text
        yield client


def _section(body: str, start: str, end: str) -> str:
    """Extract the text between two markers in the rendered homepage."""
    return body.split(start)[1].split(end)[0]


def test_root_redirects_when_theme_has_no_home(client: TestClient) -> None:
    """Default theme ships no home.html, so / keeps the historical redirect."""
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == "/posts"


def test_root_renders_home_when_theme_has_home(fake_github: FakeGitHubService) -> None:
    with home_client(fake_github) as c:
        resp = c.get("/")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")
    assert "HOME" in resp.text


def test_home_latest_posts_newest_first_excludes_drafts(fake_github: FakeGitHubService) -> None:
    with home_client(fake_github) as c:
        resp = c.get("/")
    latest = _section(resp.text, "latest:", "|featured")
    assert latest == "Post Five;Post Four;Post Three;Post Two;Post One;"
    assert "Secret Draft" not in latest


def test_home_latest_includes_drafts_for_admin(fake_github: FakeGitHubService) -> None:
    with home_client(fake_github, admin=True) as c:
        resp = c.get("/")
    latest = _section(resp.text, "latest:", "|featured")
    # The draft is the newest post, so it heads the admin latest list, and the
    # five-item cap drops the oldest published post.
    assert latest == "Secret Draft;Post Five;Post Four;Post Three;Post Two;"


def test_home_featured_populated(fake_github: FakeGitHubService) -> None:
    fake_github.files["posts/2026-02-01-featured-post.md"] = (
        "---\ntitle: Featured Post\nfeatured: true\n---\n\n# Featured Post\n\nBody.\n"
    )
    with home_client(fake_github) as c:
        resp = c.get("/")
    featured = _section(resp.text, "featured:", "|canonical")
    assert featured == "Featured Post;"


def test_home_featured_empty_without_featured_posts(fake_github: FakeGitHubService) -> None:
    with home_client(fake_github) as c:
        resp = c.get("/")
    featured = _section(resp.text, "featured:", "|canonical")
    assert featured == ""


def test_home_canonical_url(fake_github: FakeGitHubService) -> None:
    with home_client(fake_github) as c:
        resp = c.get("/")
    assert resp.text.endswith("canonical:https://test.example.com/")
