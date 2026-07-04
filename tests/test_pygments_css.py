"""Tests for dynamic pygments CSS integration."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from squishmark.config import Settings
from squishmark.models.content import Config, ThemeConfig
from squishmark.services.container import build_services
from squishmark.services.markdown import MarkdownService
from squishmark.services.theme.engine import THEME_PYGMENTS_DEFAULTS, ThemeEngine

# ---------------------------------------------------------------------------
# Unit tests for resolve_pygments_css_url
# ---------------------------------------------------------------------------


class TestResolvePygmentsCssUrl:
    """Tests for ThemeEngine.resolve_pygments_css_url."""

    def _config_with_style(self, style: str) -> Config:
        return Config(theme=ThemeConfig(pygments_style=style))

    def test_default_theme_matching_style_returns_static(self):
        """When user style matches theme default, serve static CSS."""
        url = ThemeEngine.resolve_pygments_css_url("default", self._config_with_style("github-dark"))
        assert url == "/static/default/pygments.css"

    def test_blue_tech_matching_style_returns_static(self):
        url = ThemeEngine.resolve_pygments_css_url("blue-tech", self._config_with_style("monokai"))
        assert url == "/static/blue-tech/pygments.css"

    def test_terminal_matching_style_returns_static_with_css_subdir(self):
        """Terminal theme stores CSS in css/ subdirectory."""
        url = ThemeEngine.resolve_pygments_css_url("terminal", self._config_with_style("monokai"))
        assert url == "/static/terminal/css/pygments.css"

    def test_overridden_style_returns_dynamic(self):
        """When user style differs from theme default, serve dynamic CSS."""
        url = ThemeEngine.resolve_pygments_css_url("default", self._config_with_style("dracula"))
        assert url == "/pygments.css"

    def test_unknown_theme_returns_dynamic(self):
        """Unknown themes always use dynamic CSS (no known default to match)."""
        url = ThemeEngine.resolve_pygments_css_url("custom-theme", self._config_with_style("monokai"))
        assert url == "/pygments.css"

    def test_all_bundled_themes_have_defaults(self):
        """Every bundled theme should declare its default pygments style."""
        for theme_name in ("default", "blue-tech", "terminal"):
            assert theme_name in THEME_PYGMENTS_DEFAULTS, f"Missing default for {theme_name}"


# ---------------------------------------------------------------------------
# Unit tests for get_pygments_css
# ---------------------------------------------------------------------------


def test_get_pygments_css_default_style():
    """Test that get_pygments_css returns valid CSS for the default monokai style."""
    service = MarkdownService(pygments_style="monokai")
    css = service.get_pygments_css()

    assert ".highlight" in css
    assert len(css) > 100  # Should be substantial CSS


def test_get_pygments_css_custom_style():
    """Test that get_pygments_css returns different CSS for a different style."""
    monokai = MarkdownService(pygments_style="monokai").get_pygments_css()
    dracula = MarkdownService(pygments_style="dracula").get_pygments_css()

    assert monokai != dracula
    assert ".highlight" in dracula


# ---------------------------------------------------------------------------
# Regression: Services.markdown_for follows config.pygments_style (issue #109)
# ---------------------------------------------------------------------------


def test_markdown_for_rebuilds_when_style_changes():
    """markdown_for must track the current config style, not freeze on the first."""
    services = build_services(Settings())

    md_a = services.markdown_for(Config(theme=ThemeConfig(pygments_style="monokai")))
    assert md_a.pygments_style == "monokai"

    md_b = services.markdown_for(Config(theme=ThemeConfig(pygments_style="dracula")))
    assert md_b.pygments_style == "dracula"
    assert md_a.get_pygments_css() != md_b.get_pygments_css()


def test_markdown_for_reuses_service_when_style_unchanged():
    """An unchanged style returns the same instance (cheap, but not churned)."""
    services = build_services(Settings())
    config = Config(theme=ThemeConfig(pygments_style="monokai"))

    assert services.markdown_for(config) is services.markdown_for(config)


# ---------------------------------------------------------------------------
# Integration test for /pygments.css route
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pygments_css_route():
    """Test the /pygments.css endpoint returns valid CSS."""
    mock_github = AsyncMock()
    mock_github.get_config.return_value = {
        "theme": {"name": "default", "pygments_style": "dracula"},
    }
    # Theme engine loads custom templates during the lifespan.
    mock_github.list_directory.return_value = []

    with (
        patch("squishmark.services.container.create_github_service", return_value=mock_github),
        patch("squishmark.main.init_db", new_callable=AsyncMock),
        patch("squishmark.main.close_db", new_callable=AsyncMock),
    ):
        from squishmark.main import create_app

        app = create_app()
        # ASGITransport does not emit lifespan events, so run the lifespan
        # explicitly to build the service container on app.state.
        async with app.router.lifespan_context(app):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/pygments.css")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/css; charset=utf-8"
        assert response.headers["cache-control"] == "public, no-cache"
        assert ".highlight" in response.text


@pytest.mark.asyncio
async def test_pygments_css_route_follows_config_change():
    """A pygments_style change takes effect on the next request without restart.

    Simulates the admin refresh / webhook path: after cache.clear() the next
    get_config() returns fresh config, so /pygments.css must serve the new style.
    """
    mock_github = AsyncMock()
    mock_github.get_config.return_value = {
        "theme": {"name": "default", "pygments_style": "dracula"},
    }
    mock_github.list_directory.return_value = []

    with (
        patch("squishmark.services.container.create_github_service", return_value=mock_github),
        patch("squishmark.main.init_db", new_callable=AsyncMock),
        patch("squishmark.main.close_db", new_callable=AsyncMock),
    ):
        from squishmark.main import create_app

        app = create_app()
        async with app.router.lifespan_context(app):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                first = await client.get("/pygments.css")
                # Config edit surfaces as fresh get_config output post cache clear.
                mock_github.get_config.return_value = {
                    "theme": {"name": "default", "pygments_style": "monokai"},
                }
                second = await client.get("/pygments.css")

        assert first.status_code == 200
        assert second.status_code == 200
        assert first.text != second.text
        assert second.text == MarkdownService(pygments_style="monokai").get_pygments_css()


@pytest.mark.asyncio
async def test_pygments_style_follows_cache_refresh(tmp_path):
    """The production refresh path with real caching: a config.yml edit stays
    invisible while the config is cached, then takes effect after cache.clear()
    (what the admin refresh and webhook do), with no restart."""
    from squishmark.config import Settings
    from squishmark.services.cache import Cache
    from squishmark.services.container import Services
    from squishmark.services.github import GitHubService

    config_file = tmp_path / "config.yml"
    config_file.write_text("theme:\n  pygments_style: github-dark\n", encoding="utf-8")

    settings = Settings(github_content_repo=f"file://{tmp_path}")
    cache = Cache(ttl_seconds=300)
    services = Services(settings=settings, cache=cache, github=GitHubService(settings, cache))

    config = Config.from_dict(await services.github.get_config())
    assert services.markdown_for(config).pygments_style == "github-dark"

    # Edit config.yml on disk: still cached, so the old style keeps serving.
    config_file.write_text("theme:\n  pygments_style: monokai\n", encoding="utf-8")
    config = Config.from_dict(await services.github.get_config())
    assert services.markdown_for(config).pygments_style == "github-dark"

    # The refresh (admin/webhook) clears the cache: new style takes effect.
    await cache.clear()
    config = Config.from_dict(await services.github.get_config())
    assert services.markdown_for(config).pygments_style == "monokai"
