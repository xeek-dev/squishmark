"""Tests for related-posts computation and rendering."""

import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from squishmark.models.content import Config, Post
from squishmark.services.cache import Cache
from squishmark.services.container import Services
from squishmark.services.content import build_related_posts
from squishmark.services.theme.engine import ThemeEngine

THEMES_PATH = Path(__file__).parent.parent / "themes"


def _post(slug: str, *, tags: list[str] | None = None, date: datetime.date | None = None) -> Post:
    return Post(slug=slug, title=slug.replace("-", " ").title(), tags=tags or [], date=date)


# ---------------------------------------------------------------------------
# build_related_posts
# ---------------------------------------------------------------------------


class TestBuildRelatedPosts:
    def test_ranked_by_shared_tag_count(self):
        current = _post("current", tags=["a", "b", "c"])
        two = _post("two", tags=["a", "b"], date=datetime.date(2026, 1, 1))
        one_a = _post("one-a", tags=["a"], date=datetime.date(2026, 3, 1))
        one_b = _post("one-b", tags=["b"], date=datetime.date(2026, 2, 1))
        related = build_related_posts(current, [current, one_a, two, one_b])
        # two (2 shared) first, then the two single-share posts by date desc.
        assert [p.slug for p in related] == ["two", "one-a", "one-b"]

    def test_tie_broken_by_date_desc(self):
        current = _post("current", tags=["a"])
        older = _post("older", tags=["a"], date=datetime.date(2026, 1, 1))
        newer = _post("newer", tags=["a"], date=datetime.date(2026, 6, 1))
        extra = _post("extra", tags=["a"], date=datetime.date(2026, 3, 1))
        related = build_related_posts(current, [current, older, newer, extra])
        assert [p.slug for p in related] == ["newer", "extra", "older"]

    def test_excludes_self(self):
        current = _post("current", tags=["a"])
        other = _post("other", tags=["a"])
        related = build_related_posts(current, [current, other])
        assert all(p.slug != "current" for p in related)

    def test_fallback_to_recent_when_no_overlap(self):
        current = _post("current", tags=["z"])
        r1 = _post("r1", tags=["a"], date=datetime.date(2026, 5, 1))
        r2 = _post("r2", tags=["b"], date=datetime.date(2026, 4, 1))
        r3 = _post("r3", tags=["c"], date=datetime.date(2026, 3, 1))
        related = build_related_posts(current, [current, r2, r1, r3])
        # No tag overlap -> most recent posts, newest first.
        assert [p.slug for p in related] == ["r1", "r2", "r3"]

    def test_tops_up_thin_overlap_with_recent(self):
        current = _post("current", tags=["a"])
        sharer = _post("sharer", tags=["a"], date=datetime.date(2026, 1, 1))
        recent1 = _post("recent1", tags=["x"], date=datetime.date(2026, 6, 1))
        recent2 = _post("recent2", tags=["y"], date=datetime.date(2026, 5, 1))
        related = build_related_posts(current, [current, sharer, recent1, recent2])
        # Sharer ranks first; the rest fill to minimum by date desc.
        assert related[0].slug == "sharer"
        assert [p.slug for p in related] == ["sharer", "recent1", "recent2"]

    def test_caps_at_limit(self):
        current = _post("current", tags=["a"])
        others = [_post(f"p{i}", tags=["a"], date=datetime.date(2026, 1, i + 1)) for i in range(7)]
        related = build_related_posts(current, [current, *others])
        assert len(related) == 5

    def test_no_other_posts_yields_empty(self):
        current = _post("current", tags=["a"])
        assert build_related_posts(current, [current]) == []


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


class TestRelatedRendering:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("theme", ["default", "blue-tech", "terminal"])
    async def test_related_section_rendered(self, theme: str):
        engine = _make_engine()
        config = Config.from_dict({"site": {"title": "Test"}, "theme": {"name": theme}})
        related = [_post("neighbor", tags=["a"], date=datetime.date(2026, 1, 1))]
        html = await engine.render_post(config, _post("current"), theme_override=theme, related_posts=related)
        assert 'class="related-posts"' in html
        assert 'href="/posts/neighbor"' in html
        assert "Neighbor" in html

    @pytest.mark.asyncio
    @pytest.mark.parametrize("theme", ["default", "blue-tech", "terminal"])
    async def test_related_section_hidden_when_empty(self, theme: str):
        engine = _make_engine()
        config = Config.from_dict({"site": {"title": "Test"}, "theme": {"name": theme}})
        html = await engine.render_post(config, _post("current"), theme_override=theme, related_posts=[])
        assert "related-posts" not in html
