"""Cross-theme render tests for the blue-tech homepage and posts listing (#32).

Blue-tech ships a bundled ``home.html``, so ``GET /`` renders a landing page
(hero + search + latest + featured) instead of redirecting, and ``index.html``
is a realistic ``/posts`` listing (full-width rows, tag links, pagination).

These build their own app (rather than the shared ``client`` fixture) so the
content repo and its ``config.yml`` theme selection are in place before the
lifespan runs.
"""

from contextlib import contextmanager
from typing import Any, Iterator

import pytest
from fastapi.testclient import TestClient

from squishmark.main import create_app
from tests.conftest import FakeGitHubService

pytestmark = pytest.mark.integration

BLUE_TECH_CONFIG: dict[str, Any] = {
    "site": {
        "title": "Test Blog",
        "url": "https://test.example.com",
        "description": "A blog for integration tests",
        "author": "Test Author",
    },
    "theme": {"name": "blue-tech"},
    "posts": {"per_page": 2},
}


def _post_body(title: str, *, draft: bool = False, featured: bool = False) -> str:
    lines = ["---", f"title: {title}", "tags: [python, blogging]"]
    if draft:
        lines.append("draft: true")
    if featured:
        lines.append("featured: true")
    lines.append("---")
    return "\n".join(lines) + f"\n\n# {title}\n\nBody text for {title}.\n"


def _files(*, with_featured: bool) -> dict[str, str]:
    return {
        "posts/2026-01-05-post-five.md": _post_body("Post Five", featured=with_featured),
        "posts/2026-01-04-post-four.md": _post_body("Post Four"),
        "posts/2026-01-03-post-three.md": _post_body("Post Three"),
        "posts/2026-01-02-post-two.md": _post_body("Post Two"),
        "posts/2026-01-01-post-one.md": _post_body("Post One"),
        "posts/2026-01-06-secret-draft.md": _post_body("Secret Draft", draft=True),
        "pages/about.md": "---\ntitle: About\nvisibility: public\n---\n\n# About\n\nPage body.\n",
    }


@contextmanager
def blue_tech_client(fake_github: FakeGitHubService, *, with_featured: bool = False) -> Iterator[TestClient]:
    """Yield a client whose content repo selects the blue-tech theme."""
    fake_github.config = BLUE_TECH_CONFIG
    fake_github.files = _files(with_featured=with_featured)
    app = create_app()
    with TestClient(app) as client:
        yield client


def test_home_renders_hero_latest_and_featured(fake_github: FakeGitHubService) -> None:
    with blue_tech_client(fake_github, with_featured=True) as c:
        resp = c.get("/", follow_redirects=False)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")
    body = resp.text
    # Hero
    assert 'class="hero"' in body
    assert "Latest Articles" in body
    # Search input reuses the shared partial/client
    assert 'class="hero-search"' in body
    assert 'data-search="input"' in body
    # Latest and Featured sections both present
    assert 'class="home-section"' in body
    assert ">Latest<" in body
    assert ">Featured<" in body
    # Latest lists newest-first and excludes drafts
    assert body.index("Post Five") < body.index("Post One")
    assert "Secret Draft" not in body


def test_home_hero_title_two_tone_for_single_word_camelcase(fake_github: FakeGitHubService) -> None:
    fake_github.config = {**BLUE_TECH_CONFIG, "site": {**BLUE_TECH_CONFIG["site"], "title": "SquishMark"}}
    fake_github.files = _files(with_featured=False)
    app = create_app()
    with TestClient(app) as c:
        resp = c.get("/", follow_redirects=False)
    assert resp.status_code == 200
    body = resp.text
    # Hero title splits the single CamelCase word into an accented + plain half.
    assert '<h1 class="hero-title"><span class="accent">Squish</span>Mark</h1>' in body


def test_home_hides_featured_when_none(fake_github: FakeGitHubService) -> None:
    with blue_tech_client(fake_github, with_featured=False) as c:
        resp = c.get("/", follow_redirects=False)
    assert resp.status_code == 200
    body = resp.text
    assert ">Latest<" in body
    assert ">Featured<" not in body


def test_home_ctas_point_at_real_destinations(fake_github: FakeGitHubService) -> None:
    with blue_tech_client(fake_github) as c:
        resp = c.get("/", follow_redirects=False)
    body = resp.text
    # Browse Posts goes to the real listing, not back to the current page anchor.
    assert '<a href="/posts" class="btn btn-primary">Browse Posts</a>' in body
    assert 'href="#posts"' not in body


def test_posts_listing_has_rows_tags_and_pagination(fake_github: FakeGitHubService) -> None:
    with blue_tech_client(fake_github) as c:
        resp = c.get("/posts")
    assert resp.status_code == 200
    body = resp.text
    # Full-width rows, not the hero landing
    assert 'class="posts-listing"' in body
    assert 'class="post-row"' in body
    assert 'class="hero"' not in body
    # Clickable tag chips link to /tags/{tag}
    assert 'href="/tags/python"' in body
    # Pagination present (5 published posts, per_page=2 -> 3 pages)
    assert 'class="pagination"' in body
    assert "Page 1 of 3" in body
