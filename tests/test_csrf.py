"""Tests for CSRF token generation and verification."""

import inspect
from typing import get_args
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from squishmark.dependencies import get_current_admin
from squishmark.services.csrf import (
    FORM_FIELD,
    HEADER_NAME,
    SESSION_KEY,
    get_or_create_csrf_token,
    verify_csrf_token,
)


def test_verify_csrf_token_depends_on_get_current_admin():
    """``verify_csrf_token`` must declare get_current_admin as a dependency.

    This forces FastAPI to resolve auth BEFORE the CSRF check, so unauthenticated
    HTMX requests get the 401 + HX-Redirect from auth instead of a misleading
    403 for a CSRF token they couldn't have obtained.
    """
    sig = inspect.signature(verify_csrf_token)
    admin_param = sig.parameters.get("admin")
    assert admin_param is not None, "verify_csrf_token must accept 'admin' parameter"
    # Annotation is Annotated[str, Depends(get_current_admin)]
    depends_objs = [arg for arg in get_args(admin_param.annotation) if hasattr(arg, "dependency")]
    assert depends_objs, "admin parameter must use Depends(...)"
    assert depends_objs[0].dependency is get_current_admin


def _request(
    *,
    session: dict | None = None,
    header_token: str | None = None,
    form_body: dict | None = None,
    content_type: str = "application/json",
    method: str = "POST",
    path: str = "/admin/notes",
) -> MagicMock:
    """Build a mock Request with a session dict and optional token sources."""
    request = MagicMock()
    request.session = session if session is not None else {}
    headers = {"content-type": content_type}
    if header_token is not None:
        headers[HEADER_NAME] = header_token
    request.headers = headers
    request.form = AsyncMock(return_value=form_body or {})
    request.method = method
    request.url.path = path
    return request


def test_get_or_create_csrf_token_mints_when_absent():
    request = _request()
    token = get_or_create_csrf_token(request)

    assert token
    assert len(token) > 20
    assert request.session[SESSION_KEY] == token


def test_get_or_create_csrf_token_returns_existing():
    request = _request(session={SESSION_KEY: "preexisting-token"})

    token = get_or_create_csrf_token(request)

    assert token == "preexisting-token"


def test_get_or_create_csrf_token_is_idempotent():
    """Calling twice on the same request returns the same token."""
    request = _request()

    first = get_or_create_csrf_token(request)
    second = get_or_create_csrf_token(request)

    assert first == second


@pytest.mark.asyncio
async def test_verify_csrf_token_accepts_matching_header():
    request = _request(
        session={SESSION_KEY: "good-token"},
        header_token="good-token",
    )
    with patch("squishmark.services.csrf.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(debug=False, dev_skip_auth=False)
        await verify_csrf_token(request, admin="test-admin")  # should not raise


@pytest.mark.asyncio
async def test_verify_csrf_token_rejects_missing_session_token():
    request = _request(session={}, header_token="anything")
    with patch("squishmark.services.csrf.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(debug=False, dev_skip_auth=False)
        with pytest.raises(HTTPException) as exc:
            await verify_csrf_token(request, admin="test-admin")

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_verify_csrf_token_rejects_missing_submitted_token():
    request = _request(session={SESSION_KEY: "good-token"})  # no header, no form
    with patch("squishmark.services.csrf.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(debug=False, dev_skip_auth=False)
        with pytest.raises(HTTPException) as exc:
            await verify_csrf_token(request, admin="test-admin")

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_verify_csrf_token_error_message_is_generic():
    """The error detail must not leak which check (session vs submitted) failed."""
    request_no_session = _request(session={}, header_token="anything")
    request_no_submission = _request(session={SESSION_KEY: "good-token"})
    with patch("squishmark.services.csrf.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(debug=False, dev_skip_auth=False)
        with pytest.raises(HTTPException) as exc_a:
            await verify_csrf_token(request_no_session, admin="x")
        with pytest.raises(HTTPException) as exc_b:
            await verify_csrf_token(request_no_submission, admin="x")

    assert exc_a.value.detail == exc_b.value.detail


@pytest.mark.asyncio
async def test_verify_csrf_token_logs_rejection_reason(caplog):
    """Server-side log records the specific failure mode so operators can debug.

    The user response is generic ('CSRF validation failed') to avoid info
    disclosure, so the log is the only place this detail lives.
    """
    import logging

    caplog.set_level(logging.WARNING, logger="squishmark.services.csrf")
    request = _request(
        session={SESSION_KEY: "good"},
        header_token="wrong",
        method="POST",
        path="/admin/notes",
    )
    with patch("squishmark.services.csrf.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(debug=False, dev_skip_auth=False)
        with pytest.raises(HTTPException):
            await verify_csrf_token(request, admin="alice")

    msg = caplog.text
    assert "CSRF rejected" in msg
    assert "reason=token-mismatch" in msg
    assert "method=POST" in msg
    assert "path=/admin/notes" in msg
    assert "admin=alice" in msg


@pytest.mark.asyncio
async def test_verify_csrf_token_rejects_wrong_header():
    request = _request(
        session={SESSION_KEY: "good-token"},
        header_token="wrong-token",
    )
    with patch("squishmark.services.csrf.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(debug=False, dev_skip_auth=False)
        with pytest.raises(HTTPException) as exc:
            await verify_csrf_token(request, admin="test-admin")

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_verify_csrf_token_accepts_form_field_fallback():
    """For form submissions without the header, the csrf_token form field is honored."""
    request = _request(
        session={SESSION_KEY: "good-token"},
        form_body={FORM_FIELD: "good-token"},
        content_type="application/x-www-form-urlencoded",
    )
    with patch("squishmark.services.csrf.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(debug=False, dev_skip_auth=False)
        await verify_csrf_token(request, admin="test-admin")  # should not raise


@pytest.mark.asyncio
async def test_verify_csrf_token_header_takes_precedence_over_form():
    """A valid header passes even if the form field is wrong."""
    request = _request(
        session={SESSION_KEY: "good-token"},
        header_token="good-token",
        form_body={FORM_FIELD: "wrong"},
        content_type="application/x-www-form-urlencoded",
    )
    with patch("squishmark.services.csrf.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(debug=False, dev_skip_auth=False)
        await verify_csrf_token(request, admin="test-admin")  # header wins, no raise


@pytest.mark.asyncio
async def test_verify_csrf_token_bypassed_in_dev_skip_auth():
    """When debug and dev_skip_auth are both set, CSRF check is skipped."""
    request = _request()  # no session, no token — would normally fail
    with patch("squishmark.services.csrf.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(debug=True, dev_skip_auth=True)
        await verify_csrf_token(request, admin="test-admin")  # should not raise


@pytest.mark.asyncio
async def test_verify_csrf_token_not_bypassed_in_prod_mode():
    """dev_skip_auth without debug doesn't bypass."""
    request = _request()
    with patch("squishmark.services.csrf.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(debug=False, dev_skip_auth=True)
        with pytest.raises(HTTPException) as exc:
            await verify_csrf_token(request, admin="test-admin")

    assert exc.value.status_code == 403
