"""FastAPI application entry point."""

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from squishmark.config import get_settings
from squishmark.models.db import close_db, get_db_session, init_db
from squishmark.routers import admin, auth, pages, posts, webhooks
from squishmark.services.analytics import AnalyticsService
from squishmark.services.github import get_github_service, shutdown_github_service
from squishmark.services.theme import get_theme_engine, reset_theme_engine

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if get_settings().debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("squishmark")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup and shutdown events."""
    settings = get_settings()

    # Startup
    logger.info("Starting SquishMark")
    if settings.debug:
        logger.debug("Debug mode enabled")
        logger.debug("Content repo: %s", settings.github_content_repo)

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Pre-initialize services
    github_service = get_github_service()

    # Load custom templates if any
    await get_theme_engine(github_service)
    logger.info("Theme engine initialized")

    yield

    # Shutdown
    logger.info("Shutting down SquishMark")
    await shutdown_github_service()
    reset_theme_engine()
    await close_db()


async def track_page_view(request: Request) -> None:
    """Track a page view asynchronously (fire and forget)."""
    try:
        # Get client IP
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"

        referrer = request.headers.get("referer")
        user_agent = request.headers.get("user-agent")

        async for session in get_db_session():
            analytics = AnalyticsService(session)
            await analytics.track_view(
                path=str(request.url.path),
                ip=ip,
                referrer=referrer,
                user_agent=user_agent,
            )
            break
    except Exception as e:
        # Don't let analytics errors affect the request
        logger.warning(f"Failed to track page view: {e}")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="SquishMark",
        description="A lightweight, GitHub-powered blogging engine with Jinja2 theming",
        version="0.1.0",
        debug=settings.debug,
        lifespan=lifespan,
    )

    # Custom exception handler for HTTP exceptions
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions with appropriate response format."""
        # Check if request accepts HTML
        accept = request.headers.get("accept", "")
        if "text/html" in accept and exc.status_code == 404:
            # Return HTML 404 page
            try:
                github_service = get_github_service()
                config_data = await github_service.get_config()
                from squishmark.models.content import Config

                config = Config.from_dict(config_data)
                theme_engine = await get_theme_engine()
                html = await theme_engine.render_404(config)
                return HTMLResponse(content=html, status_code=404)
            except Exception:
                pass

        # Return JSON for API requests or if HTML rendering fails
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Handle unexpected exceptions."""
        logger.exception(f"Unhandled exception: {exc}")

        if settings.debug:
            return JSONResponse(
                status_code=500,
                content={"detail": str(exc), "type": type(exc).__name__},
            )

        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    # Add session middleware for signed cookies
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.secret_key,
        session_cookie="squishmark_session",
        max_age=86400 * 7,  # 7 days
        same_site="lax",
        https_only=not settings.debug,
    )

    # Middleware to track page views (non-blocking)
    @app.middleware("http")
    async def analytics_middleware(request: Request, call_next):
        """Track page views for non-static, non-admin requests."""
        response = await call_next(request)

        # Only track successful HTML responses
        path = request.url.path
        if (
            response.status_code == 200
            and not path.startswith("/static")
            and not path.startswith("/admin")
            and not path.startswith("/health")
            and not path.startswith("/auth")
            and not path.startswith("/webhooks")
        ):
            # Fire and forget - don't await
            asyncio.create_task(track_page_view(request))

        return response

    # Health check endpoint
    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """Health check endpoint for container orchestration."""
        return {"status": "healthy"}

    # Home page - redirect to /posts
    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request) -> RedirectResponse:
        """Redirect root to posts listing."""
        return RedirectResponse(url="/posts", status_code=302)

    # Include routers
    app.include_router(auth.router)
    app.include_router(admin.router)
    app.include_router(webhooks.router)
    app.include_router(posts.router)
    app.include_router(pages.router)  # Catch-all for static pages, must be last

    # Mount static files from default theme
    themes_path = Path(__file__).parent.parent.parent / "themes" / "default" / "static"
    if themes_path.exists():
        app.mount("/static", StaticFiles(directory=themes_path), name="static")

    return app


# Create the application instance
app = create_app()
