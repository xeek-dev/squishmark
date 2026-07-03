"""Tests for the share_urls filter and share button rendering."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from jinja2 import Environment

from squishmark.models.content import Config, Post
from squishmark.services.cache import Cache
from squishmark.services.container import Services
from squishmark.services.theme.engine import ThemeEngine
from squishmark.services.theme.filters import register_filters, share_urls

THEMES_PATH = Path(__file__).parent.parent / "themes"

CANONICAL = "https://example.com/posts/hello"


def _post(title: str = "Hello World") -> Post:
    return Post(slug="hello", title=title)


class TestShareUrls:
    def test_returns_empty_list_when_canonical_url_is_none(self):
        assert share_urls(_post(), None) == []

    def test_returns_empty_list_when_canonical_url_is_empty(self):
        assert share_urls(_post(), "") == []

    def test_returns_all_platforms_in_order(self):
        platforms = [platform for platform, _ in share_urls(_post(), CANONICAL)]
        assert platforms == ["Twitter/X", "LinkedIn", "Facebook", "Reddit", "Hacker News", "Email"]

    def test_url_is_fully_percent_encoded(self):
        results = dict(share_urls(_post(), CANONICAL))
        encoded = "https%3A%2F%2Fexample.com%2Fposts%2Fhello"
        assert results["Twitter/X"] == f"https://twitter.com/intent/tweet?url={encoded}&text=Hello%20World"
        assert results["LinkedIn"] == f"https://www.linkedin.com/sharing/share-offsite/?url={encoded}"
        assert results["Facebook"] == f"https://www.facebook.com/sharer/sharer.php?u={encoded}"
        assert results["Reddit"] == f"https://reddit.com/submit?url={encoded}&title=Hello%20World"
        assert results["Hacker News"] == f"https://news.ycombinator.com/submitlink?u={encoded}&t=Hello%20World"
        assert results["Email"] == f"mailto:?subject=Hello%20World&body={encoded}"

    def test_ampersand_in_title_is_encoded(self):
        results = dict(share_urls(_post("Cats & Dogs"), CANONICAL))
        assert "Cats%20%26%20Dogs" in results["Reddit"]
        assert "&title=Cats" in results["Reddit"]

    def test_unicode_title_is_utf8_percent_encoded(self):
        results = dict(share_urls(_post("Héllo Wörld"), CANONICAL))
        assert "H%C3%A9llo%20W%C3%B6rld" in results["Twitter/X"]

    def test_question_mark_and_equals_in_title_are_encoded(self):
        results = dict(share_urls(_post("what=up?"), CANONICAL))
        assert "what%3Dup%3F" in results["Email"]

    def test_query_string_in_url_is_encoded(self):
        results = dict(share_urls(_post(), "https://example.com/posts/hi?a=1&b=2"))
        assert "%3Fa%3D1%26b%3D2" in results["Facebook"]

    def test_object_without_title_yields_empty_title(self):
        results = dict(share_urls(object(), CANONICAL))
        assert results["Email"].startswith("mailto:?subject=&body=")

    def test_filter_is_registered(self):
        env = Environment()
        register_filters(env)
        assert env.filters["share_urls"] is share_urls


def _make_engine() -> ThemeEngine:
    github_service = MagicMock()
    github_service.list_directory = AsyncMock(return_value=[])
    github_service.get_config = AsyncMock(return_value={})
    services = Services(settings=MagicMock(), cache=Cache(ttl_seconds=0), github=github_service)
    engine = ThemeEngine(services, themes_path=THEMES_PATH)
    engine.favicon_detector.detect = AsyncMock(return_value=None)  # type: ignore[method-assign]
    return engine


class TestShareSectionRendering:
    """Share buttons render on post pages across all bundled themes."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("theme", ["default", "blue-tech", "terminal"])
    async def test_share_section_rendered_when_site_url_set(self, theme: str):
        engine = _make_engine()
        config = Config.from_dict({"site": {"title": "Test", "url": "https://example.com"}})
        html = await engine.render_post(config, _post(), theme_override=theme)
        assert 'class="post-share"' in html
        assert 'rel="noopener noreferrer"' in html
        assert "https%3A%2F%2Fexample.com%2Fposts%2Fhello" in html
        assert 'class="share-btn share-copy"' in html

    @pytest.mark.asyncio
    @pytest.mark.parametrize("theme", ["default", "blue-tech", "terminal"])
    async def test_share_section_hidden_when_site_url_unset(self, theme: str):
        engine = _make_engine()
        config = Config.from_dict({"site": {"title": "Test"}})
        html = await engine.render_post(config, _post(), theme_override=theme)
        assert "post-share" not in html
        assert "share-btn" not in html
