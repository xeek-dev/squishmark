"""Tests for the archive: year/month grouping and rendering."""

import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from squishmark.models.content import Config, Post
from squishmark.services.cache import Cache
from squishmark.services.container import Services
from squishmark.services.content import build_archive
from squishmark.services.theme.engine import ThemeEngine

THEMES_PATH = Path(__file__).parent.parent / "themes"


def _post(slug: str, date: datetime.date | None) -> Post:
    return Post(slug=slug, title=slug.replace("-", " ").title(), date=date)


# ---------------------------------------------------------------------------
# build_archive
# ---------------------------------------------------------------------------


class TestBuildArchive:
    def test_groups_by_year_then_month_newest_first(self):
        posts = [
            _post("a", datetime.date(2026, 1, 15)),
            _post("b", datetime.date(2025, 12, 31)),
            _post("c", datetime.date(2026, 1, 24)),
        ]
        archive = build_archive(posts)
        assert [y.label for y in archive] == ["2026", "2025"]
        jan = archive[0].months[0]
        assert jan.name == "January"
        # Newest post first within the month.
        assert [p.slug for p in jan.posts] == ["c", "a"]

    def test_multiple_months_sorted_desc(self):
        posts = [
            _post("mar", datetime.date(2026, 3, 1)),
            _post("jan", datetime.date(2026, 1, 1)),
            _post("feb", datetime.date(2026, 2, 1)),
        ]
        archive = build_archive(posts)
        assert [m.name for m in archive[0].months] == ["March", "February", "January"]

    def test_undated_group_is_last(self):
        posts = [
            _post("dated", datetime.date(2026, 1, 1)),
            _post("undated", None),
        ]
        archive = build_archive(posts)
        assert archive[-1].label == "Undated"
        assert archive[-1].year is None
        assert archive[-1].months[0].name == ""
        assert [p.slug for p in archive[-1].months[0].posts] == ["undated"]

    def test_only_undated(self):
        archive = build_archive([_post("x", None)])
        assert len(archive) == 1
        assert archive[0].label == "Undated"

    def test_empty(self):
        assert build_archive([]) == []


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


class TestArchiveRendering:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("theme", ["default", "blue-tech", "terminal"])
    async def test_archive_renders_groups(self, theme: str):
        engine = _make_engine()
        config = Config.from_dict({"site": {"title": "Test"}, "theme": {"name": theme}})
        years = build_archive(
            [
                _post("hello-world", datetime.date(2026, 1, 15)),
                _post("undated-thoughts", None),
            ]
        )
        html = await engine.render("archive.html", config, theme_override=theme, years=years)
        assert "2026" in html
        assert "January" in html
        assert "Hello World" in html
        assert 'href="/posts/hello-world"' in html
        assert "Undated" in html
        # Archive nav link present across themes.
        assert 'href="/archive"' in html
