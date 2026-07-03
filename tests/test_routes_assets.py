"""Tests for the /static/user asset route: traversal rejection and nested serving."""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from squishmark.services.github import GitHubBinaryFile


@asynccontextmanager
async def _client_with_github(mock_github: AsyncMock):
    """Build the app with the assets router's GitHub service mocked."""
    with patch("squishmark.routers.assets.get_github_service", return_value=mock_github):
        from squishmark.main import create_app

        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url_path",
    [
        "/static/user/..%2f..%2fconfig.css",
        "/static/user/css%2f..%2f..%2fsecret.css",
        "/static/user/..%5cwindows.css",
        "/static/user/%2fabsolute.css",
    ],
)
async def test_user_static_rejects_path_traversal(url_path: str):
    """Regression for #119: traversal paths must 404 before any file lookup."""
    mock_github = AsyncMock()
    # Would happily serve anything, proving rejection happens before lookup.
    mock_github.get_binary_file.return_value = GitHubBinaryFile(
        path="static/leak.css", content=b"leak", content_type="text/css"
    )

    async with _client_with_github(mock_github) as client:
        response = await client.get(url_path)

    assert response.status_code == 404
    mock_github.get_binary_file.assert_not_called()


@pytest.mark.asyncio
async def test_user_static_serves_nested_path():
    """A normal nested path is still looked up and served."""
    mock_github = AsyncMock()
    mock_github.get_binary_file.return_value = GitHubBinaryFile(
        path="static/css/site.css", content=b"body { color: red; }", content_type="text/css"
    )

    async with _client_with_github(mock_github) as client:
        response = await client.get("/static/user/css/site.css")

    assert response.status_code == 200
    assert response.content == b"body { color: red; }"
    assert response.headers["cache-control"] == "public, max-age=86400"
    mock_github.get_binary_file.assert_awaited_once_with("static/css/site.css")
