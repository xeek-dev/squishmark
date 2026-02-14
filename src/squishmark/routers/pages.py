"""Routes for static pages."""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from squishmark.models.content import Config
from squishmark.routers.posts import _get_all_posts, get_featured_posts
from squishmark.services.github import get_github_service
from squishmark.services.markdown import get_markdown_service
from squishmark.services.theme import get_theme_engine

router = APIRouter(tags=["pages"])


@router.get("/{slug}", response_class=HTMLResponse)
async def get_page(
    request: Request,
    slug: str,
) -> HTMLResponse:
    """
    Get a static page by slug.

    This route has lower priority than /posts routes and is designed
    to be a catch-all for pages like /about, /contact, etc.
    """
    github_service = get_github_service()

    # Get config
    config_data = await github_service.get_config()
    config = Config.from_dict(config_data)

    # Get markdown service with config
    markdown_service = get_markdown_service(config)

    # Try to find the page
    page_path = f"pages/{slug}.md"
    file = await github_service.get_file(page_path)

    if file is None:
        raise HTTPException(status_code=404, detail="Page not found")

    # Parse the page
    page = markdown_service.parse_page(page_path, file.content)

    # TODO: Get notes for this page from database
    notes: list = []

    # Featured posts for template context
    all_posts = await _get_all_posts(github_service, markdown_service)
    featured = get_featured_posts(all_posts, config.site)

    # Render
    theme_engine = await get_theme_engine(github_service)
    html = await theme_engine.render_page(config, page, notes, featured_posts=featured)

    return HTMLResponse(content=html)
