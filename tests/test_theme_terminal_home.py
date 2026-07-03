"""Integration tests for the terminal theme's split homepage and listing (#32).

The terminal theme ships a bundled ``home.html``, so ``GET /`` renders the
pixel-art hero, search, latest, and featured sections. ``index.html`` is the
``/posts`` listing with dense rows, clickable tag chips, and pagination.

The active theme is switched to ``terminal`` by mutating the injected fake's
config before the app is built, mirroring how ``test_routes_home.py`` seeds
content ahead of the lifespan.
"""

from contextlib import contextmanager
from copy import deepcopy
from typing import Iterator

import pytest
from fastapi.testclient import TestClient

from squishmark.main import create_app
from tests.conftest import DEFAULT_CONFIG, FakeGitHubService

pytestmark = pytest.mark.integration

TERMINAL_CONFIG = {**deepcopy(DEFAULT_CONFIG), "theme": {"name": "terminal"}}

# A tagged, featured post so both the home featured section and the /posts tag
# chips have something to render.
FEATURED_POST = (
    "---\n"
    "title: Featured Post\n"
    "featured: true\n"
    "description: A standout entry.\n"
    "tags:\n  - python\n  - web dev\n"
    "---\n\n# Featured Post\n\nBody.\n"
)


@contextmanager
def terminal_client(fake_github: FakeGitHubService, *, with_featured: bool = False) -> Iterator[TestClient]:
    """Yield a client whose active theme is terminal."""
    fake_github.config = TERMINAL_CONFIG
    if with_featured:
        fake_github.files["posts/2026-02-01-featured-post.md"] = FEATURED_POST
    app = create_app()
    with TestClient(app) as client:
        yield client


def test_root_renders_terminal_home(fake_github: FakeGitHubService) -> None:
    with terminal_client(fake_github) as c:
        resp = c.get("/")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")
    body = resp.text
    # Pixel-art hero moved from index.html to home.html.
    assert "hero-pixel-container" in body
    assert DEFAULT_CONFIG["site"]["description"] in body
    # Prominent terminal search input reusing the shared component.
    assert "home-search" in body
    assert 'class="search-input"' in body
    # Terminal comment-style section label and latest posts.
    assert "// latest" in body
    assert "Post Five" in body


def test_home_featured_section_present_when_featured(fake_github: FakeGitHubService) -> None:
    with terminal_client(fake_github, with_featured=True) as c:
        resp = c.get("/")
    body = resp.text
    assert "// featured" in body
    assert "Featured Post" in body


def test_home_featured_section_absent_when_none(fake_github: FakeGitHubService) -> None:
    with terminal_client(fake_github) as c:
        resp = c.get("/")
    body = resp.text
    assert "// latest" in body
    assert "// featured" not in body


def test_home_latest_excludes_drafts_for_anonymous(fake_github: FakeGitHubService) -> None:
    with terminal_client(fake_github) as c:
        resp = c.get("/")
    assert "Secret Draft" not in resp.text


def test_posts_listing_rows_tags_and_pagination(fake_github: FakeGitHubService) -> None:
    with terminal_client(fake_github, with_featured=True) as c:
        resp = c.get("/posts")
    assert resp.status_code == 200
    body = resp.text
    # Dense listing rows rather than the old pixel hero.
    assert "post-row" in body
    assert "hero-pixel-container" not in body
    # Clickable tag chip linking to the tag page (#10 pattern).
    assert 'href="/tags/python"' in body
    assert 'href="/tags/web%20dev"' in body
    # per_page=2 with 6 published posts yields multiple pages.
    assert "pagination" in body
    assert "Page 1 of" in body


def test_posts_listing_second_page(fake_github: FakeGitHubService) -> None:
    with terminal_client(fake_github) as c:
        resp = c.get("/posts?page=2")
    assert resp.status_code == 200
    assert "Newer" in resp.text
