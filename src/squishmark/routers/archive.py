"""Route for the post archive page."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from squishmark.dependencies import SiteContextDep, ThemeEngineDep, is_admin
from squishmark.services.content import build_archive, get_cached_posts

router = APIRouter(tags=["archive"])


@router.get("/archive", response_class=HTMLResponse)
async def archive(
    request: Request,
    context: SiteContextDep,
    theme_engine: ThemeEngineDep,
) -> HTMLResponse:
    """List all posts grouped by year then month, newest first."""
    include_drafts = is_admin(request)
    posts = await get_cached_posts(context.services, include_drafts=include_drafts)
    years = build_archive(posts)

    html = await theme_engine.render(
        "archive.html",
        context.config,
        years=years,
        canonical_url=theme_engine.build_canonical_url(context.config, "/archive"),
    )
    return HTMLResponse(content=html)
