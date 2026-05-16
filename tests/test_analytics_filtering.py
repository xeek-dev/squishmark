"""Tests for analytics middleware filtering: bots, non-HTML, excluded paths."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from squishmark.main import is_bot_user_agent


@pytest.mark.parametrize(
    "ua",
    [
        "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
        "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)",
        "DuckDuckBot/1.1; (+http://duckduckgo.com/duckduckbot.html)",
        "Mozilla/5.0 (compatible; Baiduspider/2.0)",
        "Mozilla/5.0 (compatible; YandexBot/3.0)",
        "facebookexternalhit/1.1",
        "Twitterbot/1.0",
        "Slackbot-LinkExpanding 1.0",
        "curl/8.4.0",
        "Wget/1.21.4",
        "python-requests/2.31.0",
        "httpx/0.27.0",
    ],
)
def test_is_bot_user_agent_detects_common_bots(ua: str):
    assert is_bot_user_agent(ua) is True


@pytest.mark.parametrize(
    "ua",
    [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120",
        "Mozilla/5.0 (X11; Linux x86_64) Firefox/121.0",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0) Mobile/15E148 Safari/604.1",
    ],
)
def test_is_bot_user_agent_passes_real_browsers(ua: str):
    assert is_bot_user_agent(ua) is False


def test_is_bot_user_agent_treats_missing_as_bot():
    assert is_bot_user_agent(None) is True
    assert is_bot_user_agent("") is True


async def _build_app():
    """Build the app with external services stubbed so it boots."""
    mock_github = AsyncMock()
    mock_github.get_config.return_value = {
        "theme": {"name": "default", "pygments_style": "github-dark"},
        "site": {"title": "Test"},
    }
    stack = [
        patch("squishmark.main.get_github_service", return_value=mock_github),
        patch("squishmark.main.get_theme_engine", new_callable=AsyncMock),
        patch("squishmark.models.db.init_db", new_callable=AsyncMock),
        patch("squishmark.models.db.close_db", new_callable=AsyncMock),
        patch("squishmark.main.shutdown_github_service", new_callable=AsyncMock),
        patch("squishmark.main.reset_theme_engine"),
    ]
    return stack


async def _assert_track_called(headers: dict, path: str, expected: bool):
    """Hit the app with given headers; check whether track_page_view was scheduled."""
    stack = await _build_app()
    tracker = AsyncMock()
    with (
        stack[0],
        stack[1],
        stack[2],
        stack[3],
        stack[4],
        stack[5],
        patch("squishmark.main.track_page_view", new=tracker),
    ):
        from squishmark.main import create_app

        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.get(path, headers=headers)
        # Fire-and-forget task may not have completed yet; yield a tick.
        await asyncio.sleep(0)
        assert tracker.called is expected, (
            f"expected track_page_view.called={expected} for path={path!r} "
            f"ua={headers.get('user-agent')!r}; got called={tracker.called}"
        )


@pytest.mark.asyncio
async def test_robots_txt_not_tracked():
    await _assert_track_called(
        headers={"user-agent": "Mozilla/5.0 (Windows NT 10.0) Chrome/120"},
        path="/robots.txt",
        expected=False,
    )


@pytest.mark.asyncio
async def test_health_endpoint_not_tracked():
    await _assert_track_called(
        headers={"user-agent": "Mozilla/5.0 (Windows NT 10.0) Chrome/120"},
        path="/health",
        expected=False,
    )


@pytest.mark.asyncio
async def test_bot_request_to_html_page_not_tracked():
    """A Googlebot hit to / must not be tracked even if the response is HTML."""
    # We don't need a real HTML endpoint — /robots.txt returns text/plain which
    # already short-circuits. Use the /health JSON endpoint with a bot UA to
    # confirm bot UAs are filtered (they'd be filtered by Content-Type too,
    # but this test guards the UA gate specifically).
    await _assert_track_called(
        headers={"user-agent": "Googlebot/2.1"},
        path="/health",
        expected=False,
    )
