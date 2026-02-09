"""Tests for the /pygments.css dynamic route."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from squishmark.services.markdown import MarkdownService, reset_markdown_service


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
