"""Page-view tracking middleware and bot User-Agent detection."""

import asyncio
import logging
import re

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

from squishmark.models.db import get_db_session
from squishmark.services.analytics import AnalyticsService

logger = logging.getLogger("squishmark")


# Common bot/crawler User-Agent substrings. Matched case-insensitively. Covers
# Googlebot, Bingbot, Baidu/Yandex/Naver/Apple/Petal, social-card fetchers
# (Twitterbot, facebookexternalhit, Slackbot, Discordbot, etc.), and headless
# scripted clients (curl, wget, python-requests, httpx).
BOT_USER_AGENT_PATTERN = re.compile(
    r"bot|crawler|spider|slurp|facebookexternalhit|curl|wget|python-requests|httpx",
    re.IGNORECASE,
)


def is_bot_user_agent(user_agent: str | None) -> bool:
    """Return True if the User-Agent looks like a bot, crawler, or scripted client."""
    if not user_agent:
        # Treat missing UA as a bot, real browsers always send one.
        return True
    return bool(BOT_USER_AGENT_PATTERN.search(user_agent))


async def track_page_view(request: Request) -> None:
    """Track a page view asynchronously (fire and forget)."""
    try:
        # Get client IP
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"

        referrer = request.headers.get("referer")
        user_agent = request.headers.get("user-agent")

        async for session in get_db_session():
            analytics = AnalyticsService(session)
            await analytics.track_view(
                path=str(request.url.path),
                ip=ip,
                referrer=referrer,
                user_agent=user_agent,
            )
            break
    except Exception as e:
        # Don't let analytics errors affect the request
        logger.warning(f"Failed to track page view: {e}")


async def analytics_middleware(request: Request, call_next):
    """Track page views for non-static, non-admin, non-bot HTML requests."""
    response = await call_next(request)

    if response.status_code != 200:
        return response

    # Only HTML pages count as page views, excludes /robots.txt,
    # /sitemap.xml, /feed.xml, /favicon.ico, /pygments.css, etc.
    if not response.headers.get("content-type", "").startswith("text/html"):
        return response

    path = request.url.path
    if (
        path.startswith("/static")
        or path.startswith("/admin")
        or path.startswith("/health")
        or path.startswith("/auth")
        or path.startswith("/webhooks")
    ):
        return response

    if is_bot_user_agent(request.headers.get("user-agent")):
        return response

    # Fire and forget - don't await
    asyncio.create_task(track_page_view(request))
    return response


def register_analytics_middleware(app: FastAPI) -> None:
    """Register the page-view tracking middleware on the app."""
    app.add_middleware(BaseHTTPMiddleware, dispatch=analytics_middleware)
