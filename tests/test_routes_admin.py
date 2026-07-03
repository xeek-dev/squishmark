"""Integration tests for admin auth gating, cache refresh, analytics, and notes.

Exercises the full dependency chain (``get_current_admin`` + ``verify_csrf_token``)
through the real app, covering the 401/403/200 auth ladder, CSRF enforcement
on ``POST /admin/cache/refresh``, ``GET /admin/analytics``, and the notes CRUD
lifecycle over HTTP (``test_admin_notes.py`` unit-tests the handlers directly;
this file drives them full-stack with a real per-test SQLite database).
"""

from typing import Any, Callable

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


def test_admin_dashboard_401_anonymous(client: TestClient) -> None:
    resp = client.get("/admin")
    assert resp.status_code == 401


def test_admin_dashboard_403_wrong_user(
    seeded_client: Callable[[dict[str, Any]], TestClient],
) -> None:
    """A logged-in user who is not in ADMIN_USERS gets 403, not 401."""
    wrong = seeded_client({"user": {"login": "not-an-admin"}})
    resp = wrong.get("/admin")
    assert resp.status_code == 403


def test_admin_dashboard_200_admin(admin_client: TestClient) -> None:
    resp = admin_client.get("/admin")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")


def test_cache_refresh_admin_with_csrf_succeeds(
    admin_client: TestClient,
    csrf_token: Callable[[TestClient], str],
) -> None:
    token = csrf_token(admin_client)
    resp = admin_client.post("/admin/cache/refresh", headers={"X-CSRF-Token": token})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "ok"
    assert set(body) == {"status", "cleared", "warmed", "duration_ms"}
    assert isinstance(body["cleared"], int)
    assert isinstance(body["warmed"], int)
    assert isinstance(body["duration_ms"], (int, float))


def test_cache_refresh_without_csrf_token_403(admin_client: TestClient) -> None:
    """Authenticated admin omitting the CSRF token is rejected by
    ``verify_csrf_token`` with 403."""
    resp = admin_client.post("/admin/cache/refresh")
    assert resp.status_code == 403


def test_cache_refresh_anonymous_401(client: TestClient) -> None:
    """Anonymous caller hits the auth dependency (401) before CSRF (403)."""
    resp = client.post("/admin/cache/refresh")
    assert resp.status_code == 401


# --- /admin/analytics --------------------------------------------------------


def test_analytics_anonymous_401(client: TestClient) -> None:
    resp = client.get("/admin/analytics")
    assert resp.status_code == 401


def test_analytics_summary_shape(admin_client: TestClient) -> None:
    resp = admin_client.get("/admin/analytics")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body) == {"total_views", "unique_visitors", "top_pages", "views_by_day", "period_days"}
    assert body["period_days"] == 30


def test_analytics_days_param(admin_client: TestClient) -> None:
    resp = admin_client.get("/admin/analytics", params={"days": 7})
    assert resp.status_code == 200
    assert resp.json()["period_days"] == 7


# --- Notes CRUD over HTTP ------------------------------------------------------


def _create_note(
    admin_client: TestClient,
    token: str,
    path: str = "/posts/post-one",
    text: str = "A note",
    is_public: bool = False,
) -> dict[str, Any]:
    resp = admin_client.post(
        "/admin/notes",
        json={"path": path, "text": text, "is_public": is_public},
        headers={"X-CSRF-Token": token},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_notes_crud_lifecycle(
    admin_client: TestClient,
    csrf_token: Callable[[TestClient], str],
) -> None:
    """Create, list, update, and delete a note through the real HTTP stack."""
    token = csrf_token(admin_client)

    # Create
    note = _create_note(admin_client, token, text="First draft")
    assert note["path"] == "/posts/post-one"
    assert note["text"] == "First draft"
    assert note["is_public"] is False
    assert note["author"] == "admin-user"

    # List includes it
    listed = admin_client.get("/admin/notes")
    assert listed.status_code == 200
    assert [n["id"] for n in listed.json()] == [note["id"]]

    # Update text and visibility
    updated = admin_client.put(
        f"/admin/notes/{note['id']}",
        json={"text": "Second draft", "is_public": True},
        headers={"X-CSRF-Token": token},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["text"] == "Second draft"
    assert updated.json()["is_public"] is True

    # Delete
    deleted = admin_client.delete(f"/admin/notes/{note['id']}", headers={"X-CSRF-Token": token})
    assert deleted.status_code == 200
    assert deleted.json() == {"status": "deleted"}

    # Gone from the list
    assert admin_client.get("/admin/notes").json() == []


def test_note_create_without_csrf_403(admin_client: TestClient) -> None:
    resp = admin_client.post("/admin/notes", json={"path": "/p", "text": "t"})
    assert resp.status_code == 403


def test_note_create_missing_fields_422(
    admin_client: TestClient,
    csrf_token: Callable[[TestClient], str],
) -> None:
    token = csrf_token(admin_client)
    resp = admin_client.post("/admin/notes", json={"path": "/p"}, headers={"X-CSRF-Token": token})
    assert resp.status_code == 422


def test_notes_anonymous_401(client: TestClient) -> None:
    assert client.get("/admin/notes").status_code == 401
    assert client.post("/admin/notes", json={"path": "/p", "text": "t"}).status_code == 401


def test_note_update_missing_404(
    admin_client: TestClient,
    csrf_token: Callable[[TestClient], str],
) -> None:
    token = csrf_token(admin_client)
    resp = admin_client.put("/admin/notes/9999", json={"text": "x"}, headers={"X-CSRF-Token": token})
    assert resp.status_code == 404


def test_note_delete_missing_404(
    admin_client: TestClient,
    csrf_token: Callable[[TestClient], str],
) -> None:
    token = csrf_token(admin_client)
    resp = admin_client.delete("/admin/notes/9999", headers={"X-CSRF-Token": token})
    assert resp.status_code == 404


def test_note_htmx_create_returns_html_partial(
    admin_client: TestClient,
    csrf_token: Callable[[TestClient], str],
) -> None:
    """An HTMX form submission gets back an HTML row partial, not JSON."""
    token = csrf_token(admin_client)
    resp = admin_client.post(
        "/admin/notes",
        data={"path": "/posts/post-two", "text": "htmx note"},
        headers={"X-CSRF-Token": token, "HX-Request": "true"},
    )
    assert resp.status_code == 201, resp.text
    assert resp.headers["content-type"].startswith("text/html")
    assert "htmx note" in resp.text


def test_note_edit_form_and_view_partials(
    admin_client: TestClient,
    csrf_token: Callable[[TestClient], str],
) -> None:
    token = csrf_token(admin_client)
    note = _create_note(admin_client, token, text="editable")

    edit = admin_client.get(f"/admin/notes/{note['id']}/edit")
    assert edit.status_code == 200
    assert edit.headers["content-type"].startswith("text/html")
    assert "editable" in edit.text

    view = admin_client.get(f"/admin/notes/{note['id']}/view")
    assert view.status_code == 200
    assert "editable" in view.text

    assert admin_client.get("/admin/notes/9999/edit").status_code == 404
    assert admin_client.get("/admin/notes/9999/view").status_code == 404
