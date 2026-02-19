"""Shared content helpers for fetching and filtering posts."""

from squishmark.models.content import Post, SiteConfig
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
