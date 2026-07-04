"""Shared content helpers for fetching and filtering posts and pages."""

import calendar
import datetime
from dataclasses import dataclass
from typing import Any

from squishmark.models.content import Config, Page, Post, SiteConfig
from squishmark.services.container import Services
from squishmark.services.github import GitHubService
from squishmark.services.markdown import MarkdownService

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


@dataclass(frozen=True)
class TagCount:
    """A tag and how many posts carry it, for the tag index."""

    name: str  # Display label (authored casing of the first occurrence)
    count: int


def build_tag_index(posts: list[Post]) -> list[TagCount]:
    """Return every tag with its post count, sorted by count desc then name.

    Tags are grouped case-insensitively (so "Python" and "python" are one
    tag); the display label is the authored casing of the first occurrence.
    ``posts`` is expected to be already draft-gated by the caller.
    """
    labels: dict[str, str] = {}
    counts: dict[str, int] = {}
    for post in posts:
        # Dedup within a post so a repeated tag is not double-counted.
        for key in {t.lower() for t in post.tags}:
            labels.setdefault(key, next(t for t in post.tags if t.lower() == key))
            counts[key] = counts.get(key, 0) + 1
    tags = [TagCount(name=labels[key], count=counts[key]) for key in counts]
    tags.sort(key=lambda t: (-t.count, t.name.lower()))
    return tags


def posts_for_tag(posts: list[Post], tag: str) -> list[Post]:
    """Return posts carrying ``tag``, matched case-insensitively.

    ``posts`` is expected to be already draft-gated by the caller. An unknown
    tag yields an empty list (callers render an empty listing, not a 404).
    """
    wanted = tag.lower()
    return [p for p in posts if any(t.lower() == wanted for t in p.tags)]


@dataclass(frozen=True)
class ArchiveMonth:
    """A month bucket within an archive year (``name`` empty for undated)."""

    month: int
    name: str
    posts: list[Post]


@dataclass(frozen=True)
class ArchiveYear:
    """A year bucket of archived posts, newest month first."""

    year: int | None  # None for the trailing "Undated" group
    label: str
    months: list[ArchiveMonth]


def build_archive(posts: list[Post]) -> list[ArchiveYear]:
    """Group posts by year then month, newest first, for the archive page.

    Dateless posts collect into a trailing "Undated" group. ``posts`` is
    expected to be already draft-gated by the caller.
    """
    buckets: dict[int, dict[int, list[Post]]] = {}
    undated: list[Post] = []
    for post in posts:
        if post.date is None:
            undated.append(post)
            continue
        buckets.setdefault(post.date.year, {}).setdefault(post.date.month, []).append(post)

    archive: list[ArchiveYear] = []
    for year in sorted(buckets, reverse=True):
        months = [
            ArchiveMonth(
                month=month,
                name=calendar.month_name[month],
                posts=sorted(
                    buckets[year][month],
                    key=lambda p: p.date or datetime.date.min,
                    reverse=True,
                ),
            )
            for month in sorted(buckets[year], reverse=True)
        ]
        archive.append(ArchiveYear(year=year, label=str(year), months=months))

    if undated:
        archive.append(ArchiveYear(year=None, label="Undated", months=[ArchiveMonth(month=0, name="", posts=undated)]))
    return archive


def build_related_posts(
    post: Post,
    all_posts: list[Post],
    *,
    limit: int = 5,
    minimum: int = 3,
) -> list[Post]:
    """Return posts related to ``post`` by shared-tag count.

    Ranked by number of shared tags descending, ties broken by date
    descending. The post itself is excluded. When fewer than ``minimum``
    posts share a tag (including zero overlap), the list is topped up with the
    most recent remaining posts so readers always get suggestions. Capped at
    ``limit``.

    ``all_posts`` is expected to be already draft-gated by the caller, so
    drafts are excluded for non-admins automatically. Mirrors
    ``build_series_context``.
    """
    post_tags = {t.lower() for t in post.tags}
    candidates = [p for p in all_posts if p.slug != post.slug]

    def date_desc_key(p: Post) -> tuple[bool, datetime.date]:
        # Dated posts sort ahead of undated; newest first under reverse sort.
        return (p.date is not None, p.date or datetime.date.min)

    scored = [(p, len(post_tags & {t.lower() for t in p.tags})) for p in candidates]
    related = [
        p
        for p, shared in sorted(
            (item for item in scored if item[1] > 0),
            key=lambda item: (item[1], *date_desc_key(item[0])),
            reverse=True,
        )
    ]

    if len(related) < minimum:
        chosen = {post.slug} | {p.slug for p in related}
        recent = sorted(
            (p for p in candidates if p.slug not in chosen),
            key=date_desc_key,
            reverse=True,
        )
        related.extend(recent[: minimum - len(related)])

    return related[:limit]


async def get_all_pages(
    github_service: GitHubService,
    markdown_service: MarkdownService,
    include_hidden: bool = False,
) -> list[Page]:
    """Fetch and parse all pages from the content repository."""
    page_files = await github_service.list_directory("pages", recursive=True)

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


async def _build_content_services(services: Services) -> tuple[GitHubService, MarkdownService]:
    """Resolve the github and markdown services from the active config."""
    github_service = services.github
    config_data = await github_service.get_config()
    config = Config.from_dict(config_data)
    return github_service, services.markdown_for(config)


async def get_cached_posts(services: Services, include_drafts: bool) -> list[Post]:
    """Return the cached parsed posts for the audience, building on miss.

    Parsing every post's markdown (including Pygments highlighting) is the
    expensive part, so one miss parses everything once with drafts included and
    caches both audience variants: the published list is just the drafts
    filtered out. Both inherit the cache TTL and are invalidated by the
    webhook's cache.clear() like every other derived blob. Mirrors
    services/search.py::get_search_index.
    """
    cache = services.cache
    key = POSTS_ALL_KEY if include_drafts else POSTS_PUBLISHED_KEY
    cached = await cache.get(key)
    if cached is not None:
        return cached

    github_service, markdown_service = await _build_content_services(services)
    posts = await get_all_posts(github_service, markdown_service, include_drafts=True)

    published = [p for p in posts if not p.draft]
    await cache.set(POSTS_ALL_KEY, posts)
    await cache.set(POSTS_PUBLISHED_KEY, published)
    return posts if include_drafts else published


async def get_cached_pages(services: Services, include_hidden: bool) -> list[Page]:
    """Return the cached parsed pages for the audience, building on miss.

    Same drafts-included-once pattern as get_cached_posts: the visible variant
    is the hidden pages filtered out. The "all" variant must only be served to
    admins.
    """
    cache = services.cache
    key = PAGES_ALL_KEY if include_hidden else PAGES_VISIBLE_KEY
    cached = await cache.get(key)
    if cached is not None:
        return cached

    github_service, markdown_service = await _build_content_services(services)
    pages = await get_all_pages(github_service, markdown_service, include_hidden=True)

    visible = [p for p in pages if p.visibility != "hidden"]
    await cache.set(PAGES_ALL_KEY, pages)
    await cache.set(PAGES_VISIBLE_KEY, visible)
    return pages if include_hidden else visible


async def warm_content_caches(services: Services) -> None:
    """Pre-build both audience variants of posts and pages (webhook/admin warm).

    One call per content type suffices: a miss builds and caches both variants.
    """
    await get_cached_posts(services, include_drafts=True)
    await get_cached_pages(services, include_hidden=True)
