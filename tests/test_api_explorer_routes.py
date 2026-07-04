"""The FastAPI API explorer must not shadow content URLs in production.

FastAPI mounts its explorer at /docs, /redoc, and /openapi.json by default.
With DEBUG off those URLs must fall through to the generic pages catch-all
so a content repo can serve its own page at any of them (issue #140).
With DEBUG on, the explorer stays available for engine development.
"""

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


def test_content_page_can_own_a_framework_url_in_production(fake_github, client: TestClient) -> None:
    fake_github.files["pages/docs.md"] = "---\ntitle: Docs\n---\n\n# Docs\n\nGuides live here.\n"
    resp = client.get("/docs")
    assert resp.status_code == 200
    assert "Guides live here" in resp.text


def test_api_explorer_absent_in_production(client: TestClient) -> None:
    resp = client.get("/docs")
    # No pages/docs.md in the default fixture content: the catch-all 404s,
    # but it must not be the Swagger UI page.
    assert "swagger" not in resp.text.lower()


def test_openapi_schema_hidden_in_production(client: TestClient) -> None:
    resp = client.get("/openapi.json")
    assert resp.status_code == 404
