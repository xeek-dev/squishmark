"""Static assets revalidate instead of caching for a day (issue #139).

Every static route sends an ETag with ``Cache-Control: public, no-cache``:
browsers keep a copy but ask before using it, so an unchanged asset costs an
empty 304 and a changed one arrives immediately after a content push.
"""

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration

CSS = b"body { color: rebeccapurple; }"


def _first_get(client: TestClient, url: str):
    resp = client.get(url)
    assert resp.status_code == 200, url
    assert resp.headers["cache-control"] == "public, no-cache"
    assert resp.headers.get("etag")
    return resp


def test_user_static_conditional_flow(fake_github, client: TestClient) -> None:
    fake_github.binary_files["static/site.css"] = CSS
    first = _first_get(client, "/static/user/site.css")

    again = client.get("/static/user/site.css", headers={"If-None-Match": first.headers["etag"]})
    assert again.status_code == 304
    assert again.content == b""
    assert again.headers["etag"] == first.headers["etag"]


def test_user_static_changed_content_misses_conditional(fake_github, client: TestClient) -> None:
    fake_github.binary_files["static/site.css"] = CSS
    first = _first_get(client, "/static/user/site.css")

    fake_github.binary_files["static/site.css"] = CSS + b"\n/* v2 */"
    changed = client.get("/static/user/site.css", headers={"If-None-Match": first.headers["etag"]})
    assert changed.status_code == 200
    assert changed.headers["etag"] != first.headers["etag"]
    assert b"v2" in changed.content


def test_theme_static_conditional_flow(client: TestClient) -> None:
    first = _first_get(client, "/static/default/style.css")
    again = client.get("/static/default/style.css", headers={"If-None-Match": first.headers["etag"]})
    assert again.status_code == 304


def test_favicon_conditional_flow(client: TestClient) -> None:
    first = _first_get(client, "/favicon.ico")
    again = client.get("/favicon.ico", headers={"If-None-Match": first.headers["etag"]})
    assert again.status_code == 304


def test_weak_etag_prefix_matches(fake_github, client: TestClient) -> None:
    fake_github.binary_files["static/site.css"] = CSS
    first = _first_get(client, "/static/user/site.css")
    weak = client.get("/static/user/site.css", headers={"If-None-Match": f"W/{first.headers['etag']}"})
    assert weak.status_code == 304
