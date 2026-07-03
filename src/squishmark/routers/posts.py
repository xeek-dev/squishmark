"""Routes for blog posts."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from squishmark.dependencies import ServicesDep, ThemeEngineDep, is_admin
from squishmark.models.content import Config, Pagination
from squishmark.models.db import get_db_session
from squishmark.services.content import build_series_context, get_cached_posts, get_featured_posts
from squishmark.services.notes import NotesService

router = APIRouter(prefix="/posts", tags=["posts"])


@router.get("", response_class=HTMLResponse)
async def list_posts(
    request: Request,
    services: ServicesDep,
    theme_engine: ThemeEngineDep,
    page: int = Query(1, ge=1),
) -> HTMLResponse:
    """List all published posts with pagination."""
    # Get config
    config_data = await services.github.get_config()
    config = Config.from_dict(config_data)

    # Get all posts (admins can see drafts)
    include_drafts = is_admin(request)
    all_posts = await get_cached_posts(services, include_drafts=include_drafts)

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

    # Featured posts for template context
    featured = get_featured_posts(all_posts, config.site)

    # Render
    html = await theme_engine.render_index(config, posts, pagination, featured_posts=featured)

    return HTMLResponse(content=html)


@router.get("/{slug}", response_class=HTMLResponse)
async def get_post(
    request: Request,
    services: ServicesDep,
    theme_engine: ThemeEngineDep,
    slug: str,
    db: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    """Get a single post by slug."""
    # Get config
    config_data = await services.github.get_config()
    config = Config.from_dict(config_data)

    # Get all posts and find the matching one (admins can see drafts)
    include_drafts = is_admin(request)
    all_posts = await get_cached_posts(services, include_drafts=include_drafts)

    post = next((p for p in all_posts if p.slug == slug), None)

    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")

    # Fetch notes (private notes only visible to admins)
    notes_service = NotesService(db)
    notes = await notes_service.get_for_path(f"/posts/{slug}", include_private=include_drafts)

    # Featured posts for template context
    featured = get_featured_posts(all_posts, config.site)

    # Series navigation context. all_posts is already draft-gated by
    # include_drafts, so drafts are automatically excluded for non-admins.
    series_context = build_series_context(post, all_posts)

    # Render
    html = await theme_engine.render_post(
        config,
        post,
        notes,
        featured_posts=featured,
        **series_context,
    )

    return HTMLResponse(content=html)
