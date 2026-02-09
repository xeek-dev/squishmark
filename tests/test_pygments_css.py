"""Tests for dynamic pygments CSS integration."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from squishmark.models.content import Config, ThemeConfig
from squishmark.services.markdown import MarkdownService, reset_markdown_service
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
        url = ThemeEngine.resolve_pygments_css_url("default", self._config_with_style("monokai"))
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
# Integration test for /pygments.css route
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pygments_css_route():
    """Test the /pygments.css endpoint returns valid CSS."""
    reset_markdown_service()

    mock_github = AsyncMock()
    mock_github.get_config.return_value = {
        "theme": {"name": "default", "pygments_style": "dracula"},
    }

    with (
        patch("squishmark.main.get_github_service", return_value=mock_github),
        patch("squishmark.main.get_theme_engine", new_callable=AsyncMock),
        patch("squishmark.models.db.init_db", new_callable=AsyncMock),
        patch("squishmark.models.db.close_db", new_callable=AsyncMock),
        patch("squishmark.main.shutdown_github_service", new_callable=AsyncMock),
        patch("squishmark.main.reset_theme_engine"),
    ):
        from squishmark.main import create_app

        app = create_app()
        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/pygments.css")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/css; charset=utf-8"
        assert response.headers["cache-control"] == "public, max-age=86400"
        assert ".highlight" in response.text

    reset_markdown_service()
