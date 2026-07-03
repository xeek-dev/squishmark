"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Request, WebSocket
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

from squishmark.config import get_settings
from squishmark.models.content import Config
from squishmark.models.db import close_db, init_db
from squishmark.routers import admin, assets, auth, feed, pages, posts, search, seo, tags, webhooks
from squishmark.services.analytics_middleware import register_analytics_middleware
from squishmark.services.container import build_services
from squishmark.services.livereload import LiveReloadService
from squishmark.services.theme import ThemeEngine

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

    # Build the service container and hang it on app.state for DI.
    services = build_services(settings)
    app.state.services = services

    # Theme engine loads custom templates from the content repo (async), so it
    # is built here rather than in build_services. It holds a back-reference to
    # the container so get_nav_pages can reach the cached content layer.
    theme_engine = ThemeEngine(services)
    await theme_engine.load_custom_templates()
    app.state.theme_engine = theme_engine
    config = Config.from_dict(await services.github.get_config())
    logger.info("Theme engine initialized (configured theme: %s)", config.theme.name)

    # Start live reload watcher in debug mode
    if settings.debug:
        services.livereload = LiveReloadService()
        await services.livereload.start()

    yield

    # Shutdown
    logger.info("Shutting down SquishMark")

    if settings.debug and services.livereload is not None:
        await services.livereload.stop()

    await services.github.close()
    await close_db()


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
                services = request.app.state.services
                config_data = await services.github.get_config()
                config = Config.from_dict(config_data)
                theme_engine = request.app.state.theme_engine
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
    register_analytics_middleware(app)

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

    # LiveReload WebSocket endpoint and middleware (debug mode only)
    if settings.debug:
        from squishmark.services.livereload import LiveReloadMiddleware

        @app.websocket("/dev/livereload")
        async def livereload_ws(websocket: WebSocket) -> None:
            """WebSocket endpoint for theme live reload notifications."""
            livereload = websocket.app.state.services.livereload
            if livereload is not None:
                await livereload.handle_websocket(websocket)

        app.add_middleware(LiveReloadMiddleware)

    # Include routers
    app.include_router(auth.router)
    app.include_router(admin.router)
    app.include_router(webhooks.router)
    app.include_router(feed.router)
    app.include_router(seo.router)
    app.include_router(search.router)
    app.include_router(assets.router)
    app.include_router(posts.router)
    app.include_router(tags.router)
    app.include_router(pages.router)  # Catch-all for static pages, must be last

    return app


# Create the application instance
app = create_app()
