"""Admin routes for notes, analytics, and cache management."""

import json
import logging
import re
import time
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from squishmark.config import get_settings
from squishmark.dependencies import AdminUser, is_htmx
from squishmark.models.content import Config
from squishmark.models.db import Note, get_db_session
from squishmark.services.analytics import AnalyticsService
from squishmark.services.cache import get_cache
from squishmark.services.csrf import get_or_create_csrf_token, verify_csrf_token
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


class CSRFTokenResponse(BaseModel):
    """Response body for the CSRF token endpoint."""

    csrf_token: str


DbSession = Annotated[AsyncSession, Depends(get_db_session)]


def _inject_dev_auth_banner(html: str) -> str:
    """Insert the dev-mode auth-bypass banner after the opening <body> tag."""
    templates_dir = Path(__file__).parent.parent / "templates"
    banner_html = (templates_dir / "dev_auth_banner.html").read_text()
    banner_css = (templates_dir / "dev_auth_banner.css").read_text()
    banner = f"<style>{banner_css}</style>{banner_html}"
    return re.sub(r"(<body[^>]*>)", r"\1" + banner, html, count=1)


def _to_note_response(note: Note) -> NoteResponse:
    """Convert an ORM ``Note`` to the JSON-serializable ``NoteResponse``."""
    return NoteResponse(
        id=note.id,
        path=note.path,
        text=note.text,
        is_public=note.is_public,
        author=note.author,
        created_at=note.created_at.isoformat(),
        updated_at=note.updated_at.isoformat(),
    )


async def _render_note_partial(template_name: str, **context: Any) -> str:
    """Render a notes admin partial using the active site theme."""
    github_service = get_github_service()
    config_data = await github_service.get_config()
    theme_name = Config.from_dict(config_data).theme.name
    theme_engine = await get_theme_engine(github_service)
    return theme_engine.render_partial(template_name, theme_override=theme_name, **context)


def _is_form_request(request: Request) -> bool:
    content_type = request.headers.get("content-type", "")
    return content_type.startswith(("application/x-www-form-urlencoded", "multipart/form-data"))


async def _load_json_body(request: Request) -> dict:
    """Decode a JSON body, raising 422 on malformed JSON to match FastAPI defaults."""
    try:
        return await request.json()
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid JSON: {exc.msg}") from exc


async def parse_note_create(request: Request) -> NoteCreate:
    """Parse a ``NoteCreate`` payload from either form data or JSON.

    HTMX submits standard HTML forms as ``application/x-www-form-urlencoded``.
    Non-HTMX API callers continue to send JSON. Validation errors are returned
    as 422 (matching FastAPI's default body-binding behavior) regardless of
    which path produced them.
    """
    if _is_form_request(request):
        form = await request.form()
        # Pass through what was actually sent: absent fields stay absent so
        # Pydantic enforces required-ness instead of silently coercing to "".
        data: dict[str, Any] = {"is_public": "is_public" in form}
        if "path" in form:
            data["path"] = str(form["path"])
        if "text" in form:
            data["text"] = str(form["text"])
    else:
        data = await _load_json_body(request)
    try:
        return NoteCreate.model_validate(data)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc


async def parse_note_update(request: Request) -> NoteUpdate:
    """Parse a ``NoteUpdate`` payload from either form data or JSON.

    Form semantics:
    - ``is_public`` is always set explicitly (True if the checkbox is present,
      False otherwise) — never None — so unchecking the checkbox actually
      persists ``is_public=False`` rather than being treated as "no change".
    - ``text`` is left absent (``None``, meaning "no change") when the form
      doesn't send it. The HTMX edit form always submits ``text`` because the
      field is ``required``, so this only affects programmatic form callers
      that intentionally omit the field.

    Validation errors are returned as 422 from both paths.
    """
    if _is_form_request(request):
        form = await request.form()
        data: dict[str, Any] = {"is_public": "is_public" in form}
        if "text" in form:
            data["text"] = str(form["text"])
    else:
        data = await _load_json_body(request)
    try:
        return NoteUpdate.model_validate(data)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc


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
    csrf_token = get_or_create_csrf_token(request)
    theme_engine = await get_theme_engine(github_service)
    try:
        html = await theme_engine.render_admin(
            config,
            user={"login": admin},
            analytics=analytics,
            notes=[_to_note_response(n) for n in notes],
            cache_size=cache.size,
            csrf_token=csrf_token,
        )
    except Exception:
        # Fallback if admin template doesn't exist
        html = (
            f"<html><body><h1>Admin Dashboard</h1><p>Welcome, {admin}</p>"
            f"<p>Total views (30d): {analytics['total_views']}</p>"
            f"<p>Unique visitors (30d): {analytics['unique_visitors']}</p>"
            f"<p>Notes: {len(notes)}</p>"
            f"<p>Cache entries: {cache.size}</p></body></html>"
        )

    # Inject dev mode banner if auth bypass is active
    settings = get_settings()
    if settings.debug and settings.dev_skip_auth:
        html = _inject_dev_auth_banner(html)

    return HTMLResponse(content=html)


# CSRF token endpoint (for JSON API callers that can't scrape the meta tag)
@router.get("/csrf")
async def get_csrf(request: Request, admin: AdminUser) -> CSRFTokenResponse:
    """Return the current CSRF token for use in subsequent mutation requests."""
    del admin  # auth side-effect only
    return CSRFTokenResponse(csrf_token=get_or_create_csrf_token(request))


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
    del admin  # auth side-effect only
    notes_service = NotesService(session)
    notes = await notes_service.get_all()
    return [_to_note_response(n) for n in notes]


@router.post(
    "/notes",
    status_code=201,
    response_model=None,
    dependencies=[Depends(verify_csrf_token)],
)
async def create_note(
    request: Request,
    admin: AdminUser,
    session: DbSession,
) -> NoteResponse | HTMLResponse:
    """Create a new note. Returns an HTML partial for HTMX, JSON otherwise."""
    note_data = await parse_note_create(request)
    notes_service = NotesService(session)
    note = await notes_service.create(
        path=note_data.path,
        text=note_data.text,
        author=admin,
        is_public=note_data.is_public,
    )
    response = _to_note_response(note)
    if is_htmx(request):
        html = await _render_note_partial("admin/_note_item.html", note=response)
        return HTMLResponse(content=html, status_code=201)
    return response


@router.put(
    "/notes/{note_id}",
    response_model=None,
    dependencies=[Depends(verify_csrf_token)],
)
async def update_note(
    request: Request,
    admin: AdminUser,
    session: DbSession,
    note_id: int,
) -> NoteResponse | HTMLResponse:
    """Update a note. Returns an HTML partial for HTMX, JSON otherwise."""
    del admin  # auth side-effect only
    note_data = await parse_note_update(request)
    notes_service = NotesService(session)
    note = await notes_service.update_note(
        note_id=note_id,
        text=note_data.text,
        is_public=note_data.is_public,
    )
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    response = _to_note_response(note)
    if is_htmx(request):
        html = await _render_note_partial("admin/_note_item.html", note=response)
        return HTMLResponse(content=html)
    return response


@router.delete(
    "/notes/{note_id}",
    response_model=None,
    dependencies=[Depends(verify_csrf_token)],
)
async def delete_note(
    request: Request,
    admin: AdminUser,
    session: DbSession,
    note_id: int,
) -> dict[str, str] | HTMLResponse:
    """Delete a note. Returns an empty 200 for HTMX so the row is removed."""
    del admin  # auth side-effect only
    notes_service = NotesService(session)
    deleted = await notes_service.delete(note_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Note not found")
    if is_htmx(request):
        return HTMLResponse(content="", status_code=200)
    return {"status": "deleted"}


@router.get("/notes/{note_id}/edit", response_class=HTMLResponse)
async def edit_note_form(
    admin: AdminUser,
    session: DbSession,
    note_id: int,
) -> HTMLResponse:
    """Return the inline edit form for a note (HTMX swap target)."""
    del admin  # auth side-effect only
    notes_service = NotesService(session)
    note = await notes_service.get_by_id(note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    html = await _render_note_partial("admin/_note_edit_form.html", note=_to_note_response(note))
    return HTMLResponse(content=html)


@router.get("/notes/{note_id}/view", response_class=HTMLResponse)
async def view_note(
    admin: AdminUser,
    session: DbSession,
    note_id: int,
) -> HTMLResponse:
    """Return the read-only note row (used by the edit form's Cancel button)."""
    del admin  # auth side-effect only
    notes_service = NotesService(session)
    note = await notes_service.get_by_id(note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    html = await _render_note_partial("admin/_note_item.html", note=_to_note_response(note))
    return HTMLResponse(content=html)


# Cache management
@router.post("/cache/refresh", dependencies=[Depends(verify_csrf_token)])
async def refresh_cache(
    admin: AdminUser,
) -> CacheRefreshResponse:
    """Clear and refresh the content cache."""
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
