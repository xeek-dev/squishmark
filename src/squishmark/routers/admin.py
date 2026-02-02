"""Admin routes for notes, analytics, and cache management."""

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from squishmark.config import get_settings
from squishmark.models.content import Config
from squishmark.models.db import get_db_session
from squishmark.services.analytics import AnalyticsService
from squishmark.services.cache import get_cache
from squishmark.services.github import get_github_service
from squishmark.services.notes import NotesService
from squishmark.services.theme import get_theme_engine, reset_theme_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


# Pydantic models for request/response
class NoteCreate(BaseModel):
    """Request body for creating a note."""

    path: str
    text: str
    is_public: bool = False


class NoteUpdate(BaseModel):
    """Request body for updating a note."""

    text: str | None = None
    is_public: bool | None = None


class NoteResponse(BaseModel):
    """Response body for a note."""

    id: int
    path: str
    text: str
    is_public: bool
    author: str
    created_at: str
    updated_at: str


class CacheRefreshResponse(BaseModel):
    """Response body for cache refresh."""

    status: str
    cleared: int
    warmed: int
    duration_ms: float


# Dependency for getting the current admin user
async def get_current_admin(request: Request) -> str:
    """
    Get the current admin user from session.

    Raises HTTPException 401 if not authenticated.
    Raises HTTPException 403 if not an admin.
    """
    settings = get_settings()

    # Dev mode auth bypass (requires both flags)
    if settings.debug and settings.dev_skip_auth:
        logger.warning("Auth bypassed - returning dev-admin user")
        return "dev-admin"

    # Check for user in session (set by OAuth callback)
    user = request.session.get("user") if hasattr(request, "session") else None

    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    if user["login"] not in settings.admin_users_list:
        raise HTTPException(status_code=403, detail="Not authorized")

    return user["login"]


AdminUser = Annotated[str, Depends(get_current_admin)]
DbSession = Annotated[AsyncSession, Depends(get_db_session)]


# Admin dashboard
@router.get("", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    admin: AdminUser,
    session: DbSession,
) -> HTMLResponse:
    """Render the admin dashboard."""
    github_service = get_github_service()

    # Get config
    config_data = await github_service.get_config()
    config = Config.from_dict(config_data)

    # Get analytics
    analytics_service = AnalyticsService(session)
    analytics = await analytics_service.get_analytics_summary(30)

    # Get notes
    notes_service = NotesService(session)
    notes = await notes_service.get_all()

    # Get cache info
    cache = get_cache()

    # Render admin template
    theme_engine = await get_theme_engine(github_service)
    try:
        html = await theme_engine.render_admin(
            config,
            user={"login": admin},
            analytics=analytics,
            notes=[
                NoteResponse(
                    id=n.id,
                    path=n.path,
                    text=n.text,
                    is_public=n.is_public,
                    author=n.author,
                    created_at=n.created_at.isoformat(),
                    updated_at=n.updated_at.isoformat(),
                )
                for n in notes
            ],
            cache_size=cache.size,
        )
        return HTMLResponse(content=html)
    except Exception:
        # Fallback if admin template doesn't exist
        return HTMLResponse(
            content=f"<h1>Admin Dashboard</h1><p>Welcome, {admin}</p>"
            f"<p>Total views (30d): {analytics['total_views']}</p>"
            f"<p>Unique visitors (30d): {analytics['unique_visitors']}</p>"
            f"<p>Notes: {len(notes)}</p>"
            f"<p>Cache entries: {cache.size}</p>"
        )


# Analytics endpoints
@router.get("/analytics")
async def get_analytics(
    admin: AdminUser,
    session: DbSession,
    days: int = 30,
) -> dict[str, Any]:
    """Get analytics summary."""
    analytics_service = AnalyticsService(session)
    return await analytics_service.get_analytics_summary(days)


# Notes endpoints
@router.get("/notes")
async def list_notes(
    admin: AdminUser,
    session: DbSession,
) -> list[NoteResponse]:
    """List all notes."""
    notes_service = NotesService(session)
    notes = await notes_service.get_all()
    return [
        NoteResponse(
            id=n.id,
            path=n.path,
            text=n.text,
            is_public=n.is_public,
            author=n.author,
            created_at=n.created_at.isoformat(),
            updated_at=n.updated_at.isoformat(),
        )
        for n in notes
    ]


@router.post("/notes", status_code=201)
async def create_note(
    admin: AdminUser,
    session: DbSession,
    note_data: NoteCreate,
) -> NoteResponse:
    """Create a new note."""
    notes_service = NotesService(session)
    note = await notes_service.create(
        path=note_data.path,
        text=note_data.text,
        author=admin,
        is_public=note_data.is_public,
    )
    return NoteResponse(
        id=note.id,
        path=note.path,
        text=note.text,
        is_public=note.is_public,
        author=note.author,
        created_at=note.created_at.isoformat(),
        updated_at=note.updated_at.isoformat(),
    )


@router.put("/notes/{note_id}")
async def update_note(
    admin: AdminUser,
    session: DbSession,
    note_id: int,
    note_data: NoteUpdate,
) -> NoteResponse:
    """Update a note."""
    notes_service = NotesService(session)
    note = await notes_service.update_note(
        note_id=note_id,
        text=note_data.text,
        is_public=note_data.is_public,
    )
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")

    return NoteResponse(
        id=note.id,
        path=note.path,
        text=note.text,
        is_public=note.is_public,
        author=note.author,
        created_at=note.created_at.isoformat(),
        updated_at=note.updated_at.isoformat(),
    )


@router.delete("/notes/{note_id}")
async def delete_note(
    admin: AdminUser,
    session: DbSession,
    note_id: int,
) -> dict[str, str]:
    """Delete a note."""
    notes_service = NotesService(session)
    deleted = await notes_service.delete(note_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Note not found")
    return {"status": "deleted"}


# Cache management
@router.post("/cache/refresh")
async def refresh_cache(
    admin: AdminUser,
) -> CacheRefreshResponse:
    """Clear and refresh the content cache."""
    import time

    start = time.time()

    # Clear the cache
    cache = get_cache()
    cleared = await cache.clear()

    # Reset theme engine to reload templates
    reset_theme_engine()

    # Warm the cache by fetching content
    github_service = get_github_service()

    # Fetch config
    await github_service.get_config(use_cache=True)

    # Fetch all posts
    post_files = await github_service.list_directory("posts", use_cache=True)
    for path in post_files:
        await github_service.get_file(path, use_cache=True)

    # Fetch all pages
    page_files = await github_service.list_directory("pages", use_cache=True)
    for path in page_files:
        await github_service.get_file(path, use_cache=True)

    # Reload theme engine
    await get_theme_engine(github_service)

    duration_ms = (time.time() - start) * 1000
    warmed = cache.size

    return CacheRefreshResponse(
        status="ok",
        cleared=cleared,
        warmed=warmed,
        duration_ms=round(duration_ms, 2),
    )
