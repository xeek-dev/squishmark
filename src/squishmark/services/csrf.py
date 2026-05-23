"""CSRF token generation and verification for admin mutation endpoints.

Tokens are stored in the signed session cookie under ``SESSION_KEY`` and
validated on POST/PUT/DELETE requests via the ``verify_csrf_token`` dependency.
Clients send the token in the ``X-CSRF-Token`` header (HTMX, JSON API) or a
``csrf_token`` form field (plain form fallback). JSON callers that cannot
read the meta tag can fetch the current token from ``GET /admin/csrf``.
"""

import logging
import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, Request

from squishmark.config import get_settings
from squishmark.dependencies import get_current_admin, is_htmx

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
    """Read the submitted CSRF token from header or form body.

    For form requests we call ``request.form()``; Starlette caches the parsed
    form on the request instance, so the route handler's subsequent
    ``request.form()`` call is served from cache and does not re-read the body.
    If Starlette ever stops caching, both paths still parse independently — but
    we'd duplicate work, not lose data.
    """
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


async def verify_csrf_token(
    request: Request,
    admin: Annotated[str, Depends(get_current_admin)],
) -> None:
    """FastAPI dependency that rejects requests missing or with an invalid CSRF token.

    Depends on :func:`get_current_admin` so authentication resolves first. This
    matters for unauthenticated HTMX requests: they get the 401 + ``HX-Redirect``
    response from auth instead of a misleading 403 for a CSRF token they had no
    way to obtain.

    Skipped when ``debug`` and ``dev_skip_auth`` are both set, matching the
    auth-bypass behavior in ``get_current_admin``.
    """
    settings = get_settings()
    if settings.debug and settings.dev_skip_auth:
        logger.warning("CSRF bypassed - dev_skip_auth is enabled")
        return

    # Single user-facing error regardless of which check fails — distinguishing
    # "no session token" from "wrong submitted token" would tell an attacker
    # whether they got a session to bind to. Server-side log records the
    # specific reason so operators can diagnose without that side-channel.
    expected = request.session.get(SESSION_KEY) if hasattr(request, "session") else None
    submitted = await _extract_submitted_token(request)
    if not expected or not submitted or not secrets.compare_digest(submitted, expected):
        if not expected:
            reason = "no-session-token"
        elif not submitted:
            reason = "no-submitted-token"
        else:
            reason = "token-mismatch"
        logger.warning(
            "CSRF rejected: reason=%s method=%s path=%s admin=%s htmx=%s",
            reason,
            request.method,
            request.url.path,
            admin,
            is_htmx(request),
        )
        raise HTTPException(status_code=403, detail="CSRF validation failed")
