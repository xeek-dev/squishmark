"""Tests for post series/collections support.

Self-contained: uses direct calls plus MagicMock, no conftest.py. Mirrors the
style of tests/test_posts.py.
"""

import datetime

import pytest

from squishmark.models.content import FrontMatter, Post
from squishmark.services.content import get_all_posts
from squishmark.services.markdown import MarkdownService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _series_context(post: Post, all_posts: list[Post]) -> dict:
    """Replicate the router's series-context computation.

    Kept in lockstep with ``get_post`` in routers/posts.py. ``all_posts`` is
    assumed already draft-gated by the caller.
    """
    if not post.series:
        return {
            "series_posts": None,
            "series_prev": None,
            "series_next": None,
            "series_index": None,
            "series_total": None,
        }
    series_posts = sorted(
        (p for p in all_posts if p.series == post.series),
        key=lambda p: (
            p.series_order is None,
            p.series_order if p.series_order is not None else 0,
            p.date or datetime.date.min,
        ),
    )
    total = len(series_posts)
    idx = next((i for i, p in enumerate(series_posts) if p.slug == post.slug), None)
    prev_post = None
    next_post = None
    index = None
    if idx is not None:
        index = idx + 1
        if idx > 0:
            prev_post = series_posts[idx - 1]
        if idx < len(series_posts) - 1:
            next_post = series_posts[idx + 1]
    return {
        "series_posts": series_posts,
        "series_prev": prev_post,
        "series_next": next_post,
        "series_index": index,
        "series_total": total,
    }


def _post(slug: str, *, series: str | None = None, series_order=None, date=None) -> Post:
    return Post(
        slug=slug,
        title=slug.replace("-", " ").title(),
        series=series,
        series_order=series_order,
        date=date,
    )


# ---------------------------------------------------------------------------
# Frontmatter parsing
# ---------------------------------------------------------------------------


class TestFrontMatterSeries:
    """Series frontmatter parsing and series_order coercion."""

    def test_series_present(self):
        fm = FrontMatter(series="My Series", series_order=2)
        assert fm.series == "My Series"
        assert fm.series_order == 2

    def test_series_absent(self):
        fm = FrontMatter(title="No Series")
        assert fm.series is None
        assert fm.series_order is None

    def test_series_order_null(self):
        fm = FrontMatter(series="S", series_order=None)
        assert fm.series_order is None

    def test_series_order_empty_string(self):
        fm = FrontMatter(series="S", series_order="")
        assert fm.series_order is None

    def test_series_order_numeric_string(self):
        fm = FrontMatter(series="S", series_order="3")
        assert fm.series_order == 3

    def test_series_order_garbage_string(self):
        """Malformed series_order must coerce to None, never raise."""
        fm = FrontMatter(series="S", series_order="not-a-number")
        assert fm.series_order is None

    def test_series_order_garbage_list(self):
        fm = FrontMatter(series="S", series_order=["bogus"])
        assert fm.series_order is None

    def test_series_order_bool_rejected(self):
        # bool is an int subclass; treat as garbage rather than 0/1.
        fm = FrontMatter(series="S", series_order=True)
        assert fm.series_order is None

    def test_series_order_float_truncated(self):
        fm = FrontMatter(series="S", series_order=2.0)
        assert fm.series_order == 2

    def test_parse_post_threads_series(self):
        md = MarkdownService()
        content = "---\ntitle: T\nseries: My Series\nseries_order: 1\n---\nBody"
        post = md.parse_post("posts/2026-01-01-t.md", content)
        assert post.series == "My Series"
        assert post.series_order == 1

    def test_parse_post_garbage_series_order_does_not_raise(self):
        md = MarkdownService()
        content = "---\ntitle: T\nseries: My Series\nseries_order: nope\n---\nBody"
        post = md.parse_post("posts/2026-01-01-t.md", content)
        assert post.series == "My Series"
        assert post.series_order is None

    def test_parse_post_no_series(self):
        md = MarkdownService()
        post = md.parse_post("posts/2026-01-01-t.md", "---\ntitle: T\n---\nBody")
        assert post.series is None
        assert post.series_order is None


# ---------------------------------------------------------------------------
# Series sorting
# ---------------------------------------------------------------------------


class TestSeriesSorting:
    """Ordering of series_posts."""

    def test_sorted_by_series_order(self):
        posts = [
            _post("c", series="S", series_order=3),
            _post("a", series="S", series_order=1),
            _post("b", series="S", series_order=2),
        ]
        ctx = _series_context(posts[0], posts)
        assert [p.slug for p in ctx["series_posts"]] == ["a", "b", "c"]

    def test_date_tiebreak_when_same_order(self):
        posts = [
            _post("late", series="S", series_order=1, date=datetime.date(2026, 2, 1)),
            _post("early", series="S", series_order=1, date=datetime.date(2026, 1, 1)),
        ]
        ctx = _series_context(posts[0], posts)
        assert [p.slug for p in ctx["series_posts"]] == ["early", "late"]

    def test_none_order_sorts_last(self):
        posts = [
            _post("unordered", series="S", series_order=None, date=datetime.date(2026, 1, 1)),
            _post("first", series="S", series_order=1, date=datetime.date(2026, 5, 1)),
        ]
        ctx = _series_context(posts[0], posts)
        assert [p.slug for p in ctx["series_posts"]] == ["first", "unordered"]

    def test_only_same_series_included(self):
        posts = [
            _post("a", series="S", series_order=1),
            _post("other", series="Different", series_order=1),
            _post("b", series="S", series_order=2),
        ]
        ctx = _series_context(posts[0], posts)
        assert [p.slug for p in ctx["series_posts"]] == ["a", "b"]


# ---------------------------------------------------------------------------
# Prev/next boundaries
# ---------------------------------------------------------------------------


class TestSeriesNavigation:
    """series_prev / series_next / index / total."""

    def _three(self):
        return [
            _post("p1", series="S", series_order=1),
            _post("p2", series="S", series_order=2),
            _post("p3", series="S", series_order=3),
        ]

    def test_first_post_has_no_prev(self):
        posts = self._three()
        ctx = _series_context(posts[0], posts)
        assert ctx["series_prev"] is None
        assert ctx["series_next"].slug == "p2"
        assert ctx["series_index"] == 1
        assert ctx["series_total"] == 3

    def test_middle_post_has_both(self):
        posts = self._three()
        ctx = _series_context(posts[1], posts)
        assert ctx["series_prev"].slug == "p1"
        assert ctx["series_next"].slug == "p3"
        assert ctx["series_index"] == 2

    def test_last_post_has_no_next(self):
        posts = self._three()
        ctx = _series_context(posts[2], posts)
        assert ctx["series_prev"].slug == "p2"
        assert ctx["series_next"] is None
        assert ctx["series_index"] == 3

    def test_post_without_series_has_no_context(self):
        posts = [_post("solo")]
        ctx = _series_context(posts[0], posts)
        assert ctx["series_posts"] is None
        assert ctx["series_prev"] is None
        assert ctx["series_next"] is None
        assert ctx["series_index"] is None
        assert ctx["series_total"] is None


# ---------------------------------------------------------------------------
# Draft gating (relies on get_all_posts draft filtering)
# ---------------------------------------------------------------------------


class TestSeriesDraftGating:
    """Drafts excluded from series for non-admins, included for admins."""

    def _mock_github(self):
        from unittest.mock import AsyncMock, MagicMock

        mock_github = AsyncMock()
        mock_github.list_directory.return_value = [
            "posts/2026-01-01-p1.md",
            "posts/2026-01-02-p2.md",
            "posts/2026-01-03-p3.md",
        ]
        mock_github.get_file.side_effect = [
            MagicMock(content="---\ntitle: P1\ndate: 2026-01-01\nseries: S\nseries_order: 1\n---\nB"),
            MagicMock(content="---\ntitle: P2\ndate: 2026-01-02\nseries: S\nseries_order: 2\ndraft: true\n---\nB"),
            MagicMock(content="---\ntitle: P3\ndate: 2026-01-03\nseries: S\nseries_order: 3\n---\nB"),
        ]
        return mock_github

    @pytest.mark.asyncio
    async def test_draft_excluded_for_non_admin(self):
        md = MarkdownService()
        all_posts = await get_all_posts(self._mock_github(), md, include_drafts=False)
        current = next(p for p in all_posts if p.slug == "p1")
        ctx = _series_context(current, all_posts)
        slugs = [p.slug for p in ctx["series_posts"]]
        assert slugs == ["p1", "p3"]
        assert ctx["series_total"] == 2
        # p1's next skips the hidden draft and lands on p3
        assert ctx["series_next"].slug == "p3"

    @pytest.mark.asyncio
    async def test_draft_included_for_admin(self):
        md = MarkdownService()
        all_posts = await get_all_posts(self._mock_github(), md, include_drafts=True)
        current = next(p for p in all_posts if p.slug == "p1")
        ctx = _series_context(current, all_posts)
        slugs = [p.slug for p in ctx["series_posts"]]
        assert slugs == ["p1", "p2", "p3"]
        assert ctx["series_total"] == 3
        assert ctx["series_next"].slug == "p2"
