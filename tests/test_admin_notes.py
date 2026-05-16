"""Tests for the admin notes CRUD endpoints (JSON + HTMX dual responses)."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.responses import HTMLResponse


def _fake_note(
    note_id: int = 1,
    path: str = "/posts/hello",
    text: str = "Original text",
    is_public: bool = False,
) -> MagicMock:
    """Build a MagicMock that mimics the ORM ``Note`` shape."""
    note = MagicMock()
    note.id = note_id
    note.path = path
    note.text = text
    note.is_public = is_public
    note.author = "test-admin"
    note.created_at = datetime(2026, 5, 16, 10, 0, 0)
    note.updated_at = datetime(2026, 5, 16, 10, 0, 0)
    return note


def _request(
    *,
    hx: bool = False,
    content_type: str = "application/json",
    json_body: dict | None = None,
    form_body: dict | None = None,
) -> MagicMock:
    """Build a mock Request with optional HTMX header and body."""
    request = MagicMock()
    headers = {"content-type": content_type}
    if hx:
        headers["HX-Request"] = "true"
    request.headers = headers
    request.json = AsyncMock(return_value=json_body or {})
    request.form = AsyncMock(return_value=form_body or {})
    return request


@pytest.mark.asyncio
async def test_create_note_json_returns_json_response():
    """POST without HX-Request returns a NoteResponse JSON object."""
    from squishmark.routers.admin import create_note

    mock_service = AsyncMock()
    mock_service.create.return_value = _fake_note(note_id=42, text="JSON note", is_public=True)

    with patch("squishmark.routers.admin.NotesService", return_value=mock_service):
        result = await create_note(
            request=_request(json_body={"path": "/posts/x", "text": "JSON note", "is_public": True}),
            admin="test-admin",
            session=AsyncMock(),
        )

    assert not isinstance(result, HTMLResponse)
    assert result.id == 42
    assert result.text == "JSON note"
    assert result.is_public is True
    mock_service.create.assert_called_once_with(path="/posts/x", text="JSON note", author="test-admin", is_public=True)


@pytest.mark.asyncio
async def test_create_note_htmx_form_returns_html_partial():
    """POST with HX-Request and form body returns an HTML partial."""
    from squishmark.routers.admin import create_note

    mock_service = AsyncMock()
    mock_service.create.return_value = _fake_note(note_id=7, text="HTMX note")

    with (
        patch("squishmark.routers.admin.NotesService", return_value=mock_service),
        patch(
            "squishmark.routers.admin._render_note_partial",
            new=AsyncMock(return_value='<div class="note-item" id="note-7"><p>HTMX note</p></div>'),
        ) as mock_render,
    ):
        result = await create_note(
            request=_request(
                hx=True,
                content_type="application/x-www-form-urlencoded",
                form_body={"path": "/posts/y", "text": "HTMX note"},
            ),
            admin="test-admin",
            session=AsyncMock(),
        )

    assert isinstance(result, HTMLResponse)
    assert result.status_code == 201
    assert b'id="note-7"' in result.body
    mock_render.assert_awaited_once()
    assert mock_render.call_args.args == ("admin/_note_item.html",)


@pytest.mark.asyncio
async def test_create_note_htmx_checkbox_omitted_persists_false():
    """When the is_public checkbox is omitted from form data, is_public=False is persisted."""
    from squishmark.routers.admin import create_note

    mock_service = AsyncMock()
    mock_service.create.return_value = _fake_note(is_public=False)

    with (
        patch("squishmark.routers.admin.NotesService", return_value=mock_service),
        patch("squishmark.routers.admin._render_note_partial", new=AsyncMock(return_value="<div></div>")),
    ):
        await create_note(
            request=_request(
                hx=True,
                content_type="application/x-www-form-urlencoded",
                form_body={"path": "/posts/z", "text": "no checkbox"},
            ),
            admin="test-admin",
            session=AsyncMock(),
        )

    mock_service.create.assert_called_once()
    assert mock_service.create.call_args.kwargs["is_public"] is False


@pytest.mark.asyncio
async def test_update_note_htmx_toggle_off_persists_false():
    """PUT form without is_public after note was public must persist is_public=False.

    Guards the checkbox semantics: unchecked checkboxes are absent from form
    data, but the user expects them to mean "off", not "no change".
    """
    from squishmark.routers.admin import update_note

    mock_service = AsyncMock()
    mock_service.update_note.return_value = _fake_note(is_public=False)

    with (
        patch("squishmark.routers.admin.NotesService", return_value=mock_service),
        patch("squishmark.routers.admin._render_note_partial", new=AsyncMock(return_value="<div></div>")),
    ):
        await update_note(
            request=_request(
                hx=True,
                content_type="application/x-www-form-urlencoded",
                form_body={"text": "still here"},
            ),
            admin="test-admin",
            session=AsyncMock(),
            note_id=1,
        )

    mock_service.update_note.assert_called_once_with(note_id=1, text="still here", is_public=False)


@pytest.mark.asyncio
async def test_update_note_not_found_raises_404():
    """PUT on a missing note returns 404."""
    from squishmark.routers.admin import update_note

    mock_service = AsyncMock()
    mock_service.update_note.return_value = None

    with patch("squishmark.routers.admin.NotesService", return_value=mock_service):
        with pytest.raises(HTTPException) as exc_info:
            await update_note(
                request=_request(json_body={"text": "x"}),
                admin="test-admin",
                session=AsyncMock(),
                note_id=999,
            )

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_note_htmx_returns_empty():
    """DELETE with HX-Request returns an empty 200 so HTMX removes the row."""
    from squishmark.routers.admin import delete_note

    mock_service = AsyncMock()
    mock_service.delete.return_value = True

    with patch("squishmark.routers.admin.NotesService", return_value=mock_service):
        result = await delete_note(
            request=_request(hx=True),
            admin="test-admin",
            session=AsyncMock(),
            note_id=1,
        )

    assert isinstance(result, HTMLResponse)
    assert result.status_code == 200
    assert result.body == b""


@pytest.mark.asyncio
async def test_delete_note_json_returns_status_dict():
    """DELETE without HX-Request preserves the original JSON contract."""
    from squishmark.routers.admin import delete_note

    mock_service = AsyncMock()
    mock_service.delete.return_value = True

    with patch("squishmark.routers.admin.NotesService", return_value=mock_service):
        result = await delete_note(
            request=_request(),
            admin="test-admin",
            session=AsyncMock(),
            note_id=1,
        )

    assert result == {"status": "deleted"}


@pytest.mark.asyncio
async def test_delete_note_not_found_raises_404():
    """DELETE on a missing note returns 404."""
    from squishmark.routers.admin import delete_note

    mock_service = AsyncMock()
    mock_service.delete.return_value = False

    with patch("squishmark.routers.admin.NotesService", return_value=mock_service):
        with pytest.raises(HTTPException) as exc_info:
            await delete_note(
                request=_request(hx=True),
                admin="test-admin",
                session=AsyncMock(),
                note_id=999,
            )

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_edit_note_form_renders_partial():
    """GET /admin/notes/{id}/edit returns the edit-form partial."""
    from squishmark.routers.admin import edit_note_form

    mock_service = AsyncMock()
    mock_service.get_by_id.return_value = _fake_note(note_id=3, text="edit me")

    rendered = '<form class="note-edit-form"><textarea>edit me</textarea></form>'
    with (
        patch("squishmark.routers.admin.NotesService", return_value=mock_service),
        patch("squishmark.routers.admin._render_note_partial", new=AsyncMock(return_value=rendered)) as mock_render,
    ):
        result = await edit_note_form(
            admin="test-admin",
            session=AsyncMock(),
            note_id=3,
        )

    assert isinstance(result, HTMLResponse)
    assert b"note-edit-form" in result.body
    assert mock_render.call_args.args == ("admin/_note_edit_form.html",)


@pytest.mark.asyncio
async def test_view_note_renders_item_partial():
    """GET /admin/notes/{id}/view returns the read-only item partial."""
    from squishmark.routers.admin import view_note

    mock_service = AsyncMock()
    mock_service.get_by_id.return_value = _fake_note(note_id=3)

    with (
        patch("squishmark.routers.admin.NotesService", return_value=mock_service),
        patch(
            "squishmark.routers.admin._render_note_partial",
            new=AsyncMock(return_value='<div class="note-item" id="note-3"></div>'),
        ) as mock_render,
    ):
        result = await view_note(
            admin="test-admin",
            session=AsyncMock(),
            note_id=3,
        )

    assert isinstance(result, HTMLResponse)
    assert b'id="note-3"' in result.body
    assert mock_render.call_args.args == ("admin/_note_item.html",)


@pytest.mark.asyncio
async def test_edit_form_not_found_raises_404():
    """GET /admin/notes/{id}/edit on a missing note returns 404."""
    from squishmark.routers.admin import edit_note_form

    mock_service = AsyncMock()
    mock_service.get_by_id.return_value = None

    with patch("squishmark.routers.admin.NotesService", return_value=mock_service):
        with pytest.raises(HTTPException) as exc_info:
            await edit_note_form(admin="test-admin", session=AsyncMock(), note_id=999)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_get_current_admin_htmx_attaches_redirect_header():
    """HTMX requests with no session get an HX-Redirect header on 401."""
    from squishmark.routers.admin import get_current_admin

    request = MagicMock()
    request.session = {}
    request.headers = {"HX-Request": "true"}

    with patch("squishmark.routers.admin.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(debug=False, dev_skip_auth=False, admin_users_list=[])
        with pytest.raises(HTTPException) as exc_info:
            await get_current_admin(request)

    assert exc_info.value.status_code == 401
    assert exc_info.value.headers == {"HX-Redirect": "/auth/login"}


@pytest.mark.asyncio
async def test_get_current_admin_non_htmx_omits_redirect_header():
    """Non-HTMX requests get a plain 401 with no HX-Redirect header."""
    from squishmark.routers.admin import get_current_admin

    request = MagicMock()
    request.session = {}
    request.headers = {}

    with patch("squishmark.routers.admin.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(debug=False, dev_skip_auth=False, admin_users_list=[])
        with pytest.raises(HTTPException) as exc_info:
            await get_current_admin(request)

    assert exc_info.value.status_code == 401
    assert exc_info.value.headers is None
