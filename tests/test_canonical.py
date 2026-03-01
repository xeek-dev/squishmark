"""Tests for canonical URL support."""

import pytest

from squishmark.models.content import Config
from squishmark.services.theme.engine import ThemeEngine


@pytest.fixture
def config_with_url() -> Config:
    return Config.from_dict(
        {
            "site": {
                "title": "Test Blog",
                "url": "https://example.com",
            },
        }
    )


@pytest.fixture
def config_without_url() -> Config:
    return Config.from_dict(
        {
            "site": {
                "title": "Test Blog",
            },
        }
    )


class TestBuildCanonicalUrl:
    def test_builds_absolute_url(self, config_with_url: Config):
        result = ThemeEngine.build_canonical_url(config_with_url, "/posts/hello")
        assert result == "https://example.com/posts/hello"

    def test_strips_trailing_slash_from_base(self):
        config = Config.from_dict({"site": {"url": "https://example.com/"}})
        result = ThemeEngine.build_canonical_url(config, "/about")
        assert result == "https://example.com/about"

    def test_returns_none_when_no_site_url(self, config_without_url: Config):
        result = ThemeEngine.build_canonical_url(config_without_url, "/posts/hello")
        assert result is None

    def test_returns_none_when_empty_site_url(self):
        config = Config.from_dict({"site": {"url": ""}})
        result = ThemeEngine.build_canonical_url(config, "/posts/hello")
        assert result is None

    def test_post_url_pattern(self, config_with_url: Config):
        result = ThemeEngine.build_canonical_url(config_with_url, "/posts/my-post")
        assert result == "https://example.com/posts/my-post"

    def test_page_url_pattern(self, config_with_url: Config):
        result = ThemeEngine.build_canonical_url(config_with_url, "/about")
        assert result == "https://example.com/about"

    def test_index_url_pattern(self, config_with_url: Config):
        result = ThemeEngine.build_canonical_url(config_with_url, "/posts")
        assert result == "https://example.com/posts"

    def test_paginated_index_url_pattern(self, config_with_url: Config):
        result = ThemeEngine.build_canonical_url(config_with_url, "/posts?page=2")
        assert result == "https://example.com/posts?page=2"
