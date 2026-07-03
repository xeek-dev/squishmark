"""Asset routes: favicon, dynamic Pygments CSS, and static file serving."""

import re
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, Response

from squishmark.config import get_settings
from squishmark.models.content import Config
from squishmark.services.github import get_github_service
from squishmark.services.markdown import get_markdown_service

router = APIRouter(tags=["assets"])

# User static files from content repository
ALLOWED_STATIC_EXTENSIONS = {".ico", ".png", ".svg", ".jpg", ".jpeg", ".webp", ".gif", ".css", ".js"}

# Theme static files - serve from theme directories with fallback
VALID_THEME_NAME = re.compile(r"^[a-zA-Z0-9_-]+$")


# Favicon endpoint - browsers request this automatically
@router.get("/favicon.ico")
async def serve_favicon() -> Response:
    """Serve favicon from content repository."""
    github_service = get_github_service()

    # Try common favicon locations in order of preference
    for path in ["static/favicon.ico", "static/favicon.png", "static/favicon.svg"]:
        file = await github_service.get_binary_file(path)
        if file:
            return Response(
                content=file.content,
                media_type=file.content_type,
                headers={"Cache-Control": "public, max-age=86400"},
            )

    raise HTTPException(status_code=404, detail="Favicon not found")


# Dynamic Pygments CSS - generates syntax highlighting styles from config
@router.get("/pygments.css")
async def serve_pygments_css() -> Response:
    """Serve dynamically generated Pygments CSS based on configured style."""
    github_service = get_github_service()
    config_data = await github_service.get_config()
    config = Config.from_dict(config_data)
    md_service = get_markdown_service(config)
    css = md_service.get_pygments_css()
    return Response(
        content=css,
        media_type="text/css",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.get("/static/user/{path:path}")
async def serve_user_static(path: str) -> Response:
    """Serve static files from the user's content repository."""
    # Security: only allow specific file extensions
    ext = Path(path).suffix.lower()
    if ext not in ALLOWED_STATIC_EXTENSIONS:
        raise HTTPException(status_code=404, detail="File not found")

    github_service = get_github_service()
    file = await github_service.get_binary_file(f"static/{path}")

    if file is None:
        raise HTTPException(status_code=404, detail="File not found")

    return Response(
        content=file.content,
        media_type=file.content_type,
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.get("/static/{theme_name}/{file_path:path}")
async def serve_theme_static(theme_name: str, file_path: str) -> Response:
    """Serve static files from theme directories with fallback to default."""
    # Security: validate theme name and file path to prevent path traversal
    if not VALID_THEME_NAME.match(theme_name):
        raise HTTPException(status_code=400, detail="Invalid theme name")
    if ".." in file_path or file_path.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid file path")

    themes_dir = Path(get_settings().resolved_themes_path)

    # Try requested theme first
    file = themes_dir / theme_name / "static" / file_path
    if file.exists() and file.is_file():
        return FileResponse(file, headers={"Cache-Control": "public, max-age=86400"})

    # Fall back to default theme
    fallback = themes_dir / "default" / "static" / file_path
    if fallback.exists() and fallback.is_file():
        return FileResponse(fallback, headers={"Cache-Control": "public, max-age=86400"})

    raise HTTPException(status_code=404, detail="Static file not found")
