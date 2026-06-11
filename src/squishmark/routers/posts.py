"""Routes for blog posts."""

import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from squishmark.dependencies import is_admin
from squishmark.models.content import Config, Pagination
from squishmark.models.db import get_db_session
from squishmark.services.content import get_all_posts, get_featured_posts
from squishmark.services.github import get_github_service
from squishmark.services.markdown import get_markdown_service
from squishmark.services.notes import NotesService
from squishmark.services.theme import get_theme_engine

router = APIRouter(prefix="/posts", tags=["posts"])


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

    # Get all posts (admins can see drafts)
    include_drafts = is_admin(request)
    all_posts = await get_all_posts(github_service, markdown_service, include_drafts=include_drafts)

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
    theme_engine = await get_theme_engine(github_service)
    html = await theme_engine.render_index(config, posts, pagination, featured_posts=featured)

    return HTMLResponse(content=html)


@router.get("/{slug}", response_class=HTMLResponse)
async def get_post(
    request: Request,
    slug: str,
    db: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    """Get a single post by slug."""
    github_service = get_github_service()

    # Get config
    config_data = await github_service.get_config()
    config = Config.from_dict(config_data)

    # Get markdown service with config
    markdown_service = get_markdown_service(config)

    # Get all posts and find the matching one (admins can see drafts)
    include_drafts = is_admin(request)
    all_posts = await get_all_posts(github_service, markdown_service, include_drafts=include_drafts)

    post = next((p for p in all_posts if p.slug == slug), None)

    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")

    # Fetch notes (private notes only visible to admins)
    notes_service = NotesService(db)
    notes = await notes_service.get_for_path(f"/posts/{slug}", include_private=include_drafts)

    # Featured posts for template context
    featured = get_featured_posts(all_posts, config.site)

    # Build series navigation context if this post belongs to a series.
    # all_posts is already draft-gated by include_drafts, so drafts are
    # automatically excluded for non-admins.
    series_posts: list | None = None
    series_prev = None
    series_next = None
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

    # Render
    theme_engine = await get_theme_engine(github_service)
    html = await theme_engine.render_post(
        config,
        post,
        notes,
        featured_posts=featured,
        series_posts=series_posts,
        series_prev=series_prev,
        series_next=series_next,
        series_index=series_index,
        series_total=series_total,
    )

    return HTMLResponse(content=html)
