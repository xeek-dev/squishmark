"""Integration tests for the catch-all /{slug} page route.

Confirms public pages render, unknown/hidden pages 404, and that a 404 with an
HTML ``Accept`` header is served as the themed HTML 404 page by the custom
exception handler in ``main.py``.
"""

from fastapi.testclient import TestClient


def test_get_page_ok(client: TestClient) -> None:
    resp = client.get("/about")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")
    assert "About" in resp.text


def test_get_page_404_unknown_slug(client: TestClient) -> None:
    resp = client.get("/no-such-page")
    assert resp.status_code == 404


def test_hidden_page_returns_404(client: TestClient) -> None:
    """``visibility: hidden`` pages 404 (pages.py:51), even though the file
    exists in the content repo."""
    resp = client.get("/secret")
    assert resp.status_code == 404


def test_html_404_returns_themed_html(client: TestClient) -> None:
    """A 404 requested with ``Accept: text/html`` is rendered as the themed
    HTML 404 page (main.py:140-148): status 404, content-type text/html."""
    resp = client.get("/no-such-page", headers={"Accept": "text/html"})
    assert resp.status_code == 404
    assert resp.headers["content-type"].startswith("text/html")


def test_404_json_for_non_html_accept(client: TestClient) -> None:
    """Without an HTML Accept header the handler falls back to JSON."""
    resp = client.get("/no-such-page", headers={"Accept": "application/json"})
    assert resp.status_code == 404
    assert resp.json() == {"detail": "Page not found"}
