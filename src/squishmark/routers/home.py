"""Route for the site homepage at ``/``."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from squishmark.dependencies import SiteContextDep, ThemeEngineDep, is_admin
from squishmark.services.content import get_cached_posts, get_featured_posts

router = APIRouter(tags=["home"])

# Number of most-recent posts exposed to home.html as latest_posts.
LATEST_POSTS_LIMIT = 5


@router.get("/", response_class=HTMLResponse, response_model=None)
async def home(
    request: Request,
    context: SiteContextDep,
    theme_engine: ThemeEngineDep,
) -> HTMLResponse | RedirectResponse:
    """Render the theme homepage, or redirect to /posts when none resolves.

    A theme opts into a distinct landing page by shipping ``home.html`` (or a
    content-repo override). Themes without one (including default) keep the
    historical 302 to the posts listing.
    """
    config = context.config
    theme_name = config.theme.name

    # The default-theme fallback is excluded, so default (which ships no
    # home.html) still redirects.
    if not theme_engine.has_template("home.html", theme_name):
        return RedirectResponse(url="/posts", status_code=302)

    # Draft-gated like /posts: admins see drafts, anonymous visitors do not.
    include_drafts = is_admin(request)
    all_posts = await get_cached_posts(context.services, include_drafts=include_drafts)
    latest_posts = all_posts[:LATEST_POSTS_LIMIT]
    featured = get_featured_posts(all_posts, config.site)

    html = await theme_engine.render(
        "home.html",
        config,
        latest_posts=latest_posts,
        featured_posts=featured,
        canonical_url=theme_engine.build_canonical_url(config, "/"),
    )
    return HTMLResponse(content=html)
