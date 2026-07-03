"""Routes for tag discovery pages."""

from urllib.parse import quote

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from squishmark.dependencies import SiteContextDep, ThemeEngineDep, is_admin
from squishmark.services.content import build_tag_index, get_cached_posts, posts_for_tag

router = APIRouter(tags=["tags"])


@router.get("/tags", response_class=HTMLResponse)
async def list_tags(
    request: Request,
    context: SiteContextDep,
    theme_engine: ThemeEngineDep,
) -> HTMLResponse:
    """List every tag with its post count (admins also count drafts)."""
    include_drafts = is_admin(request)
    posts = await get_cached_posts(context.services, include_drafts=include_drafts)
    tags = build_tag_index(posts)

    html = await theme_engine.render(
        "tags.html",
        context.config,
        tags=tags,
        canonical_url=theme_engine.build_canonical_url(context.config, "/tags"),
    )
    return HTMLResponse(content=html)


@router.get("/tags/{tag}", response_class=HTMLResponse)
async def get_tag(
    request: Request,
    context: SiteContextDep,
    theme_engine: ThemeEngineDep,
    tag: str,
) -> HTMLResponse:
    """List posts carrying ``tag`` (case-insensitive; unknown tag is empty)."""
    include_drafts = is_admin(request)
    all_posts = await get_cached_posts(context.services, include_drafts=include_drafts)
    posts = posts_for_tag(all_posts, tag)

    html = await theme_engine.render(
        "tag.html",
        context.config,
        tag=tag,
        posts=posts,
        canonical_url=theme_engine.build_canonical_url(context.config, f"/tags/{quote(tag, safe='')}"),
    )
    return HTMLResponse(content=html)
