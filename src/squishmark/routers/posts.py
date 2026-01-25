"""Routes for blog posts."""

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse

from squishmark.models.content import Config, Pagination, Post
from squishmark.services.github import GitHubService, get_github_service
from squishmark.services.markdown import MarkdownService, get_markdown_service
from squishmark.services.theme import ThemeEngine, get_theme_engine

router = APIRouter(prefix="/posts", tags=["posts"])


async def _get_all_posts(
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


@router.get("", response_class=HTMLResponse)
async def list_posts(
    request: Request,
    page: int = Query(1, ge=1),
) -> HTMLResponse:
    """List all published posts with pagination."""
    github_service = get_github_service()

    # Get config
    config_data = await github_service.get_config()
    config = Config.from_dict(config_data)

    # Get markdown service with config
    markdown_service = get_markdown_service(config)

    # Get all posts
    all_posts = await _get_all_posts(github_service, markdown_service)

    # Paginate
    per_page = config.posts.per_page
    total_items = len(all_posts)
    total_pages = (total_items + per_page - 1) // per_page if total_items > 0 else 1

    # Clamp page number
    page = min(page, total_pages)

    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    posts = all_posts[start_idx:end_idx]

    pagination = Pagination(
        page=page,
        per_page=per_page,
        total_items=total_items,
        total_pages=total_pages,
    )

    # Render
    theme_engine = await get_theme_engine(github_service)
    html = await theme_engine.render_index(config, posts, pagination)

    return HTMLResponse(content=html)


@router.get("/{slug}", response_class=HTMLResponse)
async def get_post(
    request: Request,
    slug: str,
) -> HTMLResponse:
    """Get a single post by slug."""
    github_service = get_github_service()

    # Get config
    config_data = await github_service.get_config()
    config = Config.from_dict(config_data)

    # Get markdown service with config
    markdown_service = get_markdown_service(config)

    # Get all posts and find the matching one
    all_posts = await _get_all_posts(github_service, markdown_service)

    post = next((p for p in all_posts if p.slug == slug), None)

    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")

    # TODO: Get notes for this post from database
    notes: list = []

    # Render
    theme_engine = await get_theme_engine(github_service)
    html = await theme_engine.render_post(config, post, notes)

    return HTMLResponse(content=html)
