"""Asset routes: favicon, dynamic Pygments CSS, and static file serving."""

import hashlib
import mimetypes
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from squishmark.config import get_settings
from squishmark.dependencies import ServicesDep, SiteContextDep

router = APIRouter(tags=["assets"])

# User static files from content repository
ALLOWED_STATIC_EXTENSIONS = {".ico", ".png", ".svg", ".jpg", ".jpeg", ".webp", ".gif", ".css", ".js"}

# Theme static files - serve from theme directories with fallback
VALID_THEME_NAME = re.compile(r"^[a-zA-Z0-9_-]+$")

# Cache but revalidate on every use: a repeat visit costs one conditional
# request answered with an empty 304 while the asset is unchanged, and picks
# up a pushed change immediately when it isn't (issue #139). The old
# max-age=86400 let browsers show day-old assets after a content push.
CACHE_CONTROL = "public, no-cache"


def _etag_for(content: bytes) -> str:
    return f'"{hashlib.sha256(content).hexdigest()[:32]}"'


def _conditional_response(request: Request, content: bytes, media_type: str) -> Response:
    """Serve *content* with an ETag, or an empty 304 when the client's copy matches."""
    etag = _etag_for(content)
    headers = {"Cache-Control": CACHE_CONTROL, "ETag": etag}

    if_none_match = request.headers.get("if-none-match", "")
    client_tags = [tag.strip().removeprefix("W/") for tag in if_none_match.split(",") if tag.strip()]
    if etag in client_tags or "*" in client_tags:
        return Response(status_code=304, headers=headers)

    return Response(content=content, media_type=media_type, headers=headers)


# Favicon endpoint - browsers request this automatically
@router.get("/favicon.ico")
async def serve_favicon(request: Request, services: ServicesDep) -> Response:
    """Serve favicon from content repository."""
    # Try common favicon locations in order of preference
    for path in ["static/favicon.ico", "static/favicon.png", "static/favicon.svg"]:
        file = await services.github.get_binary_file(path)
        if file:
            return _conditional_response(request, file.content, file.content_type)

    raise HTTPException(status_code=404, detail="Favicon not found")


# Dynamic Pygments CSS - generates syntax highlighting styles from config
@router.get("/pygments.css")
async def serve_pygments_css(request: Request, context: SiteContextDep) -> Response:
    """Serve dynamically generated Pygments CSS based on configured style."""
    css = context.markdown.get_pygments_css()
    return _conditional_response(request, css.encode("utf-8"), "text/css")


@router.get("/static/user/{path:path}")
async def serve_user_static(request: Request, services: ServicesDep, path: str) -> Response:
    """Serve static files from the user's content repository."""
    # Security: reject path traversal (matters in local content mode)
    if ".." in path or "\\" in path or path.startswith("/"):
        raise HTTPException(status_code=404, detail="File not found")

    # Security: only allow specific file extensions
    ext = Path(path).suffix.lower()
    if ext not in ALLOWED_STATIC_EXTENSIONS:
        raise HTTPException(status_code=404, detail="File not found")

    file = await services.github.get_binary_file(f"static/{path}")

    if file is None:
        raise HTTPException(status_code=404, detail="File not found")

    return _conditional_response(request, file.content, file.content_type)


@router.get("/static/{theme_name}/{file_path:path}")
async def serve_theme_static(request: Request, theme_name: str, file_path: str) -> Response:
    """Serve static files from theme directories with fallback to default."""
    # Security: validate theme name and file path to prevent path traversal
    if not VALID_THEME_NAME.match(theme_name):
        raise HTTPException(status_code=400, detail="Invalid theme name")
    if ".." in file_path or file_path.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid file path")

    themes_dir = Path(get_settings().resolved_themes_path)

    for candidate in (
        themes_dir / theme_name / "static" / file_path,
        themes_dir / "default" / "static" / file_path,  # fallback
    ):
        if candidate.exists() and candidate.is_file():
            media_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
            return _conditional_response(request, candidate.read_bytes(), media_type)

    raise HTTPException(status_code=404, detail="Static file not found")
