"""Shared content helpers for fetching and filtering posts and pages."""

import datetime
from typing import Any

from squishmark.models.content import Page, Post, SiteConfig
from squishmark.services.github import GitHubService
from squishmark.services.markdown import MarkdownService


async def get_all_posts(
    github_service: GitHubService,
    markdown_service: MarkdownService,
    include_drafts: bool = False,
) -> list[Post]:
    """Fetch and parse all posts from the content repository."""
    post_files = await github_service.list_directory("posts")

    posts: list[Post] = []
    for path in post_files:
        if not path.endswith(".md"):
            continue

        file = await github_service.get_file(path)
        if file is None:
            continue

        post = markdown_service.parse_post(path, file.content)

        # Skip drafts unless requested
        if post.draft and not include_drafts:
            continue

        posts.append(post)

    # Sort by date (newest first), posts without dates go last
    posts.sort(key=lambda p: (p.date is not None, p.date), reverse=True)

    return posts


def get_featured_posts(posts: list[Post], site_config: SiteConfig) -> list[Post]:
    """Filter and sort featured posts from a list of posts.

    Sort order: featured_order ascending (nulls last), then date descending.
    Limited to site_config.featured_max entries.
    """
    featured = [p for p in posts if p.featured]
    featured.sort(
        key=lambda p: (
            0 if p.featured_order is not None else 1,
            p.featured_order if p.featured_order is not None else 0,
            -(p.date.toordinal() if p.date else 0),
        ),
    )
    return featured[: site_config.featured_max]


def build_series_context(post: Post, all_posts: list[Post]) -> dict[str, Any]:
    """Build the series-navigation template context for a post.

    Returns a dict whose keys match ``ThemeEngine.render_post``'s series
    kwargs (``series_posts``, ``series_prev``, ``series_next``,
    ``series_index``, ``series_total``) so callers can splat it directly.
    All values are None when the post does not belong to a series.

    ``all_posts`` is expected to be already draft-gated by the caller
    (``get_all_posts(..., include_drafts=...)``), so drafts are excluded
    from series navigation for non-admins automatically.

    Series posts sort by ``series_order`` ascending (nulls last), then date.
    """
    series_posts: list[Post] | None = None
    series_prev: Post | None = None
    series_next: Post | None = None
    series_index: int | None = None
    series_total: int | None = None
    if post.series:
        series_posts = sorted(
            (p for p in all_posts if p.series == post.series),
            key=lambda p: (
                p.series_order is None,
                p.series_order if p.series_order is not None else 0,
                p.date or datetime.date.min,
            ),
        )
        series_total = len(series_posts)
        current_idx = next(
            (i for i, p in enumerate(series_posts) if p.slug == post.slug),
            None,
        )
        if current_idx is not None:
            series_index = current_idx + 1
            if current_idx > 0:
                series_prev = series_posts[current_idx - 1]
            if current_idx < len(series_posts) - 1:
                series_next = series_posts[current_idx + 1]
    return {
        "series_posts": series_posts,
        "series_prev": series_prev,
        "series_next": series_next,
        "series_index": series_index,
        "series_total": series_total,
    }


async def get_all_pages(
    github_service: GitHubService,
    markdown_service: MarkdownService,
    include_hidden: bool = False,
) -> list[Page]:
    """Fetch and parse all pages from the content repository."""
    page_files = await github_service.list_directory("pages")

    pages: list[Page] = []
    for path in page_files:
        if not path.endswith(".md"):
            continue

        file = await github_service.get_file(path)
        if file is None:
            continue

        page = markdown_service.parse_page(path, file.content)

        # Skip hidden pages unless requested
        if page.visibility == "hidden" and not include_hidden:
            continue

        pages.append(page)

    return pages
