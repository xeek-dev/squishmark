"""CSRF token generation and verification for admin mutation endpoints.

Tokens are stored in the signed session cookie under ``SESSION_KEY`` and
validated on POST/PUT/DELETE requests via the ``verify_csrf_token`` dependency.
Clients send the token in the ``X-CSRF-Token`` header (HTMX, JSON API) or a
``csrf_token`` form field (plain form fallback).
"""

import logging
import secrets

from fastapi import HTTPException, Request

from squishmark.config import get_settings

logger = logging.getLogger(__name__)

SESSION_KEY = "csrf_token"
HEADER_NAME = "X-CSRF-Token"
FORM_FIELD = "csrf_token"


def get_or_create_csrf_token(request: Request) -> str:
    """Return the session's CSRF token, minting a new one if absent."""
    token = request.session.get(SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        request.session[SESSION_KEY] = token
    return token


async def _extract_submitted_token(request: Request) -> str | None:
    """Read the submitted CSRF token from header or form body."""
    header_token = request.headers.get(HEADER_NAME)
    if header_token:
        return header_token

    content_type = request.headers.get("content-type", "")
    if content_type.startswith(("application/x-www-form-urlencoded", "multipart/form-data")):
        form = await request.form()
        value = form.get(FORM_FIELD)
        if isinstance(value, str):
            return value
    return None


async def verify_csrf_token(request: Request) -> None:
    """FastAPI dependency that rejects requests missing or with an invalid CSRF token.

    Skipped when ``debug`` and ``dev_skip_auth`` are both set, matching the
    auth-bypass behavior in ``get_current_admin``.
    """
    settings = get_settings()
    if settings.debug and settings.dev_skip_auth:
        logger.warning("CSRF bypassed - dev_skip_auth is enabled")
        return

    expected = request.session.get(SESSION_KEY) if hasattr(request, "session") else None
    if not expected:
        raise HTTPException(status_code=403, detail="CSRF token missing from session")

    submitted = await _extract_submitted_token(request)
    if not submitted or not secrets.compare_digest(submitted, expected):
        raise HTTPException(status_code=403, detail="CSRF token invalid")
