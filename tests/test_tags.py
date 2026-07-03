"""Tests for tag discovery: index building, filtering, and rendering.

Unit tests exercise the pure helpers directly; the render tests drive the
real ThemeEngine against the bundled themes, mirroring test_share_urls.py.
"""

import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from squishmark.models.content import Config, Post
from squishmark.services.cache import Cache
from squishmark.services.container import Services
from squishmark.services.content import build_tag_index, posts_for_tag
from squishmark.services.theme.engine import ThemeEngine

THEMES_PATH = Path(__file__).parent.parent / "themes"


def _post(slug: str, *, tags: list[str] | None = None, date: datetime.date | None = None) -> Post:
    return Post(slug=slug, title=slug.replace("-", " ").title(), tags=tags or [], date=date)


# ---------------------------------------------------------------------------
# build_tag_index
# ---------------------------------------------------------------------------


class TestBuildTagIndex:
    def test_counts_posts_per_tag(self):
        posts = [
            _post("a", tags=["python", "cooking"]),
            _post("b", tags=["python"]),
            _post("c", tags=["aliens"]),
        ]
        index = {t.name: t.count for t in build_tag_index(posts)}
        assert index == {"python": 2, "cooking": 1, "aliens": 1}

    def test_sorted_by_count_desc_then_name(self):
        posts = [
            _post("a", tags=["python", "zeta"]),
            _post("b", tags=["python", "alpha"]),
            _post("c", tags=["alpha"]),
        ]
        result = [(t.name, t.count) for t in build_tag_index(posts)]
        # alpha and python tie at 2, so name ascending breaks the tie; zeta (1) last
        assert result == [("alpha", 2), ("python", 2), ("zeta", 1)]

    def test_case_insensitive_grouping(self):
        posts = [
            _post("a", tags=["Python"]),
            _post("b", tags=["python"]),
            _post("c", tags=["PYTHON"]),
        ]
        index = build_tag_index(posts)
        assert len(index) == 1
        assert index[0].count == 3
        # Display label is the first-seen authored casing.
        assert index[0].name == "Python"

    def test_repeated_tag_in_one_post_counts_once(self):
        posts = [_post("a", tags=["python", "Python"])]
        index = build_tag_index(posts)
        assert len(index) == 1
        assert index[0].count == 1

    def test_empty_posts_yields_empty_index(self):
        assert build_tag_index([]) == []


# ---------------------------------------------------------------------------
# posts_for_tag
# ---------------------------------------------------------------------------


class TestPostsForTag:
    def test_matches_case_insensitively(self):
        posts = [
            _post("a", tags=["Python"]),
            _post("b", tags=["cooking"]),
            _post("c", tags=["python", "aliens"]),
        ]
        assert [p.slug for p in posts_for_tag(posts, "PYTHON")] == ["a", "c"]

    def test_unknown_tag_yields_empty(self):
        posts = [_post("a", tags=["python"])]
        assert posts_for_tag(posts, "nonexistent") == []

    def test_preserves_input_order(self):
        posts = [
            _post("newest", tags=["x"], date=datetime.date(2026, 3, 1)),
            _post("older", tags=["x"], date=datetime.date(2026, 1, 1)),
        ]
        assert [p.slug for p in posts_for_tag(posts, "x")] == ["newest", "older"]


# ---------------------------------------------------------------------------
# Cross-theme rendering
# ---------------------------------------------------------------------------


def _make_engine() -> ThemeEngine:
    github_service = MagicMock()
    github_service.list_directory = AsyncMock(return_value=[])
    github_service.get_config = AsyncMock(return_value={})
    github_service.get_file = AsyncMock(return_value=None)
    services = Services(settings=MagicMock(), cache=Cache(ttl_seconds=0), github=github_service)
    engine = ThemeEngine(services, themes_path=THEMES_PATH)
    engine.favicon_detector.detect = AsyncMock(return_value=None)  # type: ignore[method-assign]
    return engine


THEMES = ["default", "blue-tech", "terminal"]


class TestTagRendering:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("theme", THEMES)
    async def test_tags_index_lists_tags_and_counts(self, theme: str):
        engine = _make_engine()
        config = Config.from_dict({"site": {"title": "Test"}, "theme": {"name": theme}})
        tags = build_tag_index([_post("a", tags=["python", "cooking"]), _post("b", tags=["python"])])
        html = await engine.render("tags.html", config, theme_override=theme, tags=tags)
        assert 'href="/tags/python"' in html
        assert 'href="/tags/cooking"' in html
        assert ">2<" in html  # python count
        # Tags nav link is present across themes.
        assert 'href="/tags"' in html

    @pytest.mark.asyncio
    @pytest.mark.parametrize("theme", THEMES)
    async def test_tag_page_lists_matching_posts(self, theme: str):
        engine = _make_engine()
        config = Config.from_dict({"site": {"title": "Test"}, "theme": {"name": theme}})
        posts = [_post("hello-world", tags=["python"], date=datetime.date(2026, 1, 1))]
        html = await engine.render("tag.html", config, theme_override=theme, tag="python", posts=posts)
        assert "Hello World" in html
        assert 'href="/posts/hello-world"' in html
        assert "python" in html

    @pytest.mark.asyncio
    @pytest.mark.parametrize("theme", THEMES)
    async def test_tag_page_empty_listing(self, theme: str):
        engine = _make_engine()
        config = Config.from_dict({"site": {"title": "Test"}, "theme": {"name": theme}})
        html = await engine.render("tag.html", config, theme_override=theme, tag="ghost", posts=[])
        assert "ghost" in html
        assert "No posts" in html
