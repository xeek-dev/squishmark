"""Tests for content service helpers."""

from datetime import date
from typing import Any

import pytest

from squishmark.models.content import Post, SiteConfig
from squishmark.services.cache import Cache
from squishmark.services.container import Services
from squishmark.services.content import (
    PAGES_ALL_KEY,
    PAGES_VISIBLE_KEY,
    POSTS_ALL_KEY,
    POSTS_PUBLISHED_KEY,
    get_cached_pages,
    get_cached_posts,
    get_featured_posts,
    warm_content_caches,
)
from squishmark.services.github import GitHubFile


def _make_post(
    slug: str,
    featured: bool = True,
    featured_order: int | None = None,
    post_date: date | None = None,
) -> Post:
    return Post(slug=slug, title=slug, featured=featured, featured_order=featured_order, date=post_date)


class TestGetFeaturedPosts:
    """Tests for featured post sort logic."""

    def test_featured_order_nulls_last(self):
        """Posts with explicit featured_order sort before those without."""
        posts = [
            _make_post("no-order", featured_order=None, post_date=date(2026, 3, 1)),
            _make_post("order-2", featured_order=2, post_date=date(2026, 1, 1)),
            _make_post("order-1", featured_order=1, post_date=date(2026, 2, 1)),
        ]
        result = get_featured_posts(posts, SiteConfig())
        slugs = [p.slug for p in result]
        assert slugs == ["order-1", "order-2", "no-order"]

    def test_featured_date_tiebreak(self):
        """Posts without explicit order break ties by date descending."""
        posts = [
            _make_post("older", post_date=date(2026, 1, 1)),
            _make_post("newer", post_date=date(2026, 3, 1)),
            _make_post("middle", post_date=date(2026, 2, 1)),
        ]
        result = get_featured_posts(posts, SiteConfig())
        slugs = [p.slug for p in result]
        assert slugs == ["newer", "middle", "older"]

    def test_non_featured_excluded(self):
        """Posts with featured=False are excluded from results."""
        posts = [
            _make_post("yes", featured=True),
            _make_post("no", featured=False),
        ]
        result = get_featured_posts(posts, SiteConfig())
        assert [p.slug for p in result] == ["yes"]

    def test_featured_max_limits_results(self):
        """featured_max caps the number of returned posts."""
        posts = [_make_post(f"post-{i}", featured_order=i) for i in range(5)]
        result = get_featured_posts(posts, SiteConfig(featured_max=2))
        assert len(result) == 2
        assert result[0].slug == "post-0"


_CONFIG: dict[str, Any] = {"site": {"title": "Test"}, "theme": {"name": "default"}}


def _post_md(title: str, *, draft: bool = False) -> str:
    draft_line = "draft: true\n" if draft else ""
    return f"---\ntitle: {title}\n{draft_line}---\n\n# {title}\n\nBody.\n"


def _page_md(title: str, *, visibility: str = "public") -> str:
    return f"---\ntitle: {title}\nvisibility: {visibility}\n---\n\n# {title}\n\nBody.\n"


class _CountingGitHub:
    """Fake GitHub service counting get_file calls to prove parse reuse."""

    def __init__(self, files: dict[str, str]) -> None:
        self.files = files
        self.get_file_calls = 0

    async def get_config(self, use_cache: bool = True) -> dict[str, Any]:
        return _CONFIG

    async def list_directory(
        self, path: str, ref: str = "main", use_cache: bool = True, recursive: bool = False
    ) -> list[str]:
        prefix = f"{path.rstrip('/')}/"
        return sorted(k for k in self.files if k.startswith(prefix) and (recursive or "/" not in k[len(prefix) :]))

    async def get_file(self, path: str, ref: str = "main", use_cache: bool = True) -> GitHubFile | None:
        self.get_file_calls += 1
        content = self.files.get(path)
        return None if content is None else GitHubFile(path=path, content=content)


@pytest.fixture
def fake_github() -> _CountingGitHub:
    """A counting fake with a fixed set of posts and pages."""
    files = {
        "posts/2026-01-02-published.md": _post_md("Published"),
        "posts/2026-01-03-secret.md": _post_md("Secret", draft=True),
        "pages/about.md": _page_md("About"),
        "pages/hidden.md": _page_md("Hidden", visibility="hidden"),
    }
    return _CountingGitHub(files)


@pytest.fixture
def services(fake_github: _CountingGitHub) -> Services:
    """A service container wrapping the counting fake and a real cache.

    A non-zero TTL keeps entries alive across calls so the reuse assertions
    hold (a zero TTL expires entries immediately).
    """
    from squishmark.config import get_settings

    cache = Cache(ttl_seconds=get_settings().cache_ttl_seconds)
    return Services(settings=get_settings(), cache=cache, github=fake_github)


class TestGetCachedPosts:
    """Draft gating, audience-variant caching, and invalidation for posts."""

    @pytest.mark.asyncio
    async def test_published_variant_excludes_drafts(self, services: Services) -> None:
        published = await get_cached_posts(services, include_drafts=False)
        assert [p.slug for p in published] == ["published"]

    @pytest.mark.asyncio
    async def test_all_variant_includes_drafts(self, services: Services) -> None:
        all_posts = await get_cached_posts(services, include_drafts=True)
        assert {p.slug for p in all_posts} == {"published", "secret"}

    @pytest.mark.asyncio
    async def test_one_miss_caches_both_variants(self, services: Services, fake_github: _CountingGitHub) -> None:
        """A single published miss must also populate the admin variant, so the
        admin request that follows never re-parses (and never leaks the other
        way around)."""
        await get_cached_posts(services, include_drafts=False)
        after_first = fake_github.get_file_calls
        assert after_first > 0

        # The drafts-included variant is served from the same miss: no re-fetch.
        all_posts = await get_cached_posts(services, include_drafts=True)
        assert fake_github.get_file_calls == after_first
        assert {p.slug for p in all_posts} == {"published", "secret"}

    @pytest.mark.asyncio
    async def test_repeat_call_does_not_refetch(self, services: Services, fake_github: _CountingGitHub) -> None:
        await get_cached_posts(services, include_drafts=False)
        after_first = fake_github.get_file_calls
        await get_cached_posts(services, include_drafts=False)
        assert fake_github.get_file_calls == after_first

    @pytest.mark.asyncio
    async def test_clear_invalidates(self, services: Services, fake_github: _CountingGitHub) -> None:
        await get_cached_posts(services, include_drafts=False)
        after_first = fake_github.get_file_calls
        await services.cache.clear()
        await get_cached_posts(services, include_drafts=False)
        assert fake_github.get_file_calls > after_first


class TestGetCachedPages:
    """Hidden gating, audience-variant caching, and invalidation for pages."""

    @pytest.mark.asyncio
    async def test_visible_variant_excludes_hidden(self, services: Services) -> None:
        visible = await get_cached_pages(services, include_hidden=False)
        assert [p.slug for p in visible] == ["about"]

    @pytest.mark.asyncio
    async def test_all_variant_includes_hidden(self, services: Services) -> None:
        all_pages = await get_cached_pages(services, include_hidden=True)
        assert {p.slug for p in all_pages} == {"about", "hidden"}

    @pytest.mark.asyncio
    async def test_one_miss_caches_both_variants(self, services: Services, fake_github: _CountingGitHub) -> None:
        await get_cached_pages(services, include_hidden=False)
        after_first = fake_github.get_file_calls
        all_pages = await get_cached_pages(services, include_hidden=True)
        assert fake_github.get_file_calls == after_first
        assert {p.slug for p in all_pages} == {"about", "hidden"}


class TestWarmContentCaches:
    @pytest.mark.asyncio
    async def test_warm_populates_all_variants(self, services: Services) -> None:
        await warm_content_caches(services)
        cache = services.cache
        assert await cache.get(POSTS_ALL_KEY) is not None
        assert await cache.get(POSTS_PUBLISHED_KEY) is not None
        assert await cache.get(PAGES_ALL_KEY) is not None
        assert await cache.get(PAGES_VISIBLE_KEY) is not None
