"""Analytics service for tracking and reporting page views."""

import hashlib
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from squishmark.models.db import PageView


class AnalyticsService:
    """Service for tracking and querying page view analytics."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def hash_ip(ip: str) -> str:
        """Create a SHA256 hash of an IP address for privacy."""
        return hashlib.sha256(ip.encode()).hexdigest()

    async def track_view(
        self,
        path: str,
        ip: str,
        referrer: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """
        Track a page view.

        Args:
            path: The page path that was viewed
            ip: Visitor's IP address (will be hashed)
            referrer: HTTP referrer header
            user_agent: User agent string
        """
        view = PageView(
            path=path,
            ip_hash=self.hash_ip(ip),
            referrer=referrer[:1000] if referrer else None,
            user_agent=user_agent[:500] if user_agent else None,
        )
        self.session.add(view)
        await self.session.flush()

    async def get_total_views(self, days: int | None = None) -> int:
        """Get total page views, optionally filtered by time period."""
        query = select(func.count(PageView.id))

        if days is not None:
            since = datetime.now() - timedelta(days=days)
            query = query.where(PageView.timestamp >= since)

        result = await self.session.execute(query)
        return result.scalar() or 0

    async def get_unique_visitors(self, days: int | None = None) -> int:
        """Get count of unique visitors (by IP hash), optionally filtered by time period."""
        query = select(func.count(func.distinct(PageView.ip_hash)))

        if days is not None:
            since = datetime.now() - timedelta(days=days)
            query = query.where(PageView.timestamp >= since)

        result = await self.session.execute(query)
        return result.scalar() or 0

    async def get_top_pages(
        self,
        limit: int = 10,
        days: int | None = None,
    ) -> list[dict[str, Any]]:
        """Get the most viewed pages."""
        query = (
            select(PageView.path, func.count(PageView.id).label("views"))
            .group_by(PageView.path)
            .order_by(func.count(PageView.id).desc())
            .limit(limit)
        )

        if days is not None:
            since = datetime.now() - timedelta(days=days)
            query = query.where(PageView.timestamp >= since)

        result = await self.session.execute(query)
        return [{"path": row.path, "views": row.views} for row in result.all()]

    async def get_views_by_day(
        self,
        days: int = 30,
    ) -> list[dict[str, Any]]:
        """Get page views grouped by day for charting."""
        since = datetime.now() - timedelta(days=days)

        # SQLite-specific date formatting
        query = (
            select(
                func.date(PageView.timestamp).label("date"),
                func.count(PageView.id).label("views"),
                func.count(func.distinct(PageView.ip_hash)).label("unique_visitors"),
            )
            .where(PageView.timestamp >= since)
            .group_by(func.date(PageView.timestamp))
            .order_by(func.date(PageView.timestamp))
        )

        result = await self.session.execute(query)
        return [
            {
                "date": str(row.date),
                "views": row.views,
                "unique_visitors": row.unique_visitors,
            }
            for row in result.all()
        ]

    async def get_analytics_summary(self, days: int = 30) -> dict[str, Any]:
        """Get a complete analytics summary for the admin dashboard."""
        total_views = await self.get_total_views(days)
        unique_visitors = await self.get_unique_visitors(days)
        top_pages = await self.get_top_pages(10, days)
        views_by_day = await self.get_views_by_day(days)

        return {
            "total_views": total_views,
            "unique_visitors": unique_visitors,
            "top_pages": top_pages,
            "views_by_day": views_by_day,
            "period_days": days,
        }
