"""Routes for static pages."""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from squishmark.dependencies import SiteContextDep, ThemeEngineDep, is_admin
from squishmark.models.db import get_db_session
from squishmark.services.content import get_cached_posts, get_featured_posts
from squishmark.services.notes import NotesService

router = APIRouter(tags=["pages"])


@router.get("/{slug:path}", response_class=HTMLResponse)
async def get_page(
    request: Request,
    context: SiteContextDep,
    theme_engine: ThemeEngineDep,
    slug: str,
    db: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    """
    Get a static page by slug, including nested pages like /docs/setup.

    This route has lower priority than /posts routes and is designed
    to be a catch-all for pages like /about, /contact, etc.
    """
    config = context.config
    markdown_service = context.markdown

    # Reject empty, dot, and traversal segments before touching the content store
    if not slug or any(not seg or seg.startswith(".") for seg in slug.split("/")):
        raise HTTPException(status_code=404, detail="Page not found")

    # Try to find the page
    page_path = f"pages/{slug}.md"
    file = await context.services.github.get_file(page_path)

    if file is None:
        raise HTTPException(status_code=404, detail="Page not found")

    # Parse the page
    page = markdown_service.parse_page(page_path, file.content)

    # Hidden pages return 404
    if page.visibility == "hidden":
        raise HTTPException(status_code=404, detail="Page not found")

    # Fetch notes (private notes only visible to admins)
    admin = is_admin(request)
    notes_service = NotesService(db)
    notes = await notes_service.get_for_path(f"/{slug}", include_private=admin)

    # Featured posts for template context (published only, shown to everyone)
    all_posts = await get_cached_posts(context.services, include_drafts=False)
    featured = get_featured_posts(all_posts, config.site)

    # Render
    html = await theme_engine.render_page(config, page, notes, featured_posts=featured)

    return HTMLResponse(content=html)
