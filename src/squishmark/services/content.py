"""Shared content helpers for fetching and filtering posts and pages."""

import datetime
from typing import Any

from squishmark.models.content import Config, Page, Post, SiteConfig
from squishmark.services.cache import get_cache
from squishmark.services.github import GitHubService, get_github_service
from squishmark.services.markdown import MarkdownService, get_markdown_service

# Audience-separated cache keys. The "all" variants include drafts (posts) and
# hidden pages, so they must only ever be served to admins: sharing a key would
# leak unpublished content to anonymous visitors. Mirrors the search index keys.
POSTS_ALL_KEY = "content:posts:all"
POSTS_PUBLISHED_KEY = "content:posts:published"
PAGES_ALL_KEY = "content:pages:all"
PAGES_VISIBLE_KEY = "content:pages:visible"


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


async def _build_content_services() -> tuple[GitHubService, MarkdownService]:
    """Resolve the github and markdown services from the active config."""
    github_service = get_github_service()
    config_data = await github_service.get_config()
    config = Config.from_dict(config_data)
    return github_service, get_markdown_service(config)


async def get_cached_posts(include_drafts: bool) -> list[Post]:
    """Return the cached parsed posts for the audience, building on miss.

    Parsing every post's markdown (including Pygments highlighting) is the
    expensive part, so one miss parses everything once with drafts included and
    caches both audience variants: the published list is just the drafts
    filtered out. Both inherit the cache TTL and are invalidated by the
    webhook's cache.clear() like every other derived blob. Mirrors
    services/search.py::get_search_index.
    """
    cache = get_cache()
    key = POSTS_ALL_KEY if include_drafts else POSTS_PUBLISHED_KEY
    cached = await cache.get(key)
    if cached is not None:
        return cached

    github_service, markdown_service = await _build_content_services()
    posts = await get_all_posts(github_service, markdown_service, include_drafts=True)

    published = [p for p in posts if not p.draft]
    await cache.set(POSTS_ALL_KEY, posts)
    await cache.set(POSTS_PUBLISHED_KEY, published)
    return posts if include_drafts else published


async def get_cached_pages(include_hidden: bool) -> list[Page]:
    """Return the cached parsed pages for the audience, building on miss.

    Same drafts-included-once pattern as get_cached_posts: the visible variant
    is the hidden pages filtered out. The "all" variant must only be served to
    admins.
    """
    cache = get_cache()
    key = PAGES_ALL_KEY if include_hidden else PAGES_VISIBLE_KEY
    cached = await cache.get(key)
    if cached is not None:
        return cached

    github_service, markdown_service = await _build_content_services()
    pages = await get_all_pages(github_service, markdown_service, include_hidden=True)

    visible = [p for p in pages if p.visibility != "hidden"]
    await cache.set(PAGES_ALL_KEY, pages)
    await cache.set(PAGES_VISIBLE_KEY, visible)
    return pages if include_hidden else visible


async def warm_content_caches() -> None:
    """Pre-build both audience variants of posts and pages (webhook/admin warm).

    One call per content type suffices: a miss builds and caches both variants.
    """
    await get_cached_posts(include_drafts=True)
    await get_cached_pages(include_hidden=True)
