"""Tests for content service helpers."""

from datetime import date

from squishmark.models.content import Post, SiteConfig
from squishmark.services.content import get_featured_posts


def _make_post(
    slug: str,
    featured: bool = True,
    featured_order: int | None = None,
    post_date: date | None = None,
) -> Post:
    return Post(slug=slug, title=slug, featured=featured, featured_order=featured_order, date=post_date)


class TestGetFeaturedPosts:
    """Tests for featured post sort logic."""

    def test_featured_order_nulls_last(self):
        """Posts with explicit featured_order sort before those without."""
        posts = [
            _make_post("no-order", featured_order=None, post_date=date(2026, 3, 1)),
            _make_post("order-2", featured_order=2, post_date=date(2026, 1, 1)),
            _make_post("order-1", featured_order=1, post_date=date(2026, 2, 1)),
        ]
        result = get_featured_posts(posts, SiteConfig())
        slugs = [p.slug for p in result]
        assert slugs == ["order-1", "order-2", "no-order"]

    def test_featured_date_tiebreak(self):
        """Posts without explicit order break ties by date descending."""
        posts = [
            _make_post("older", post_date=date(2026, 1, 1)),
            _make_post("newer", post_date=date(2026, 3, 1)),
            _make_post("middle", post_date=date(2026, 2, 1)),
        ]
        result = get_featured_posts(posts, SiteConfig())
        slugs = [p.slug for p in result]
        assert slugs == ["newer", "middle", "older"]
