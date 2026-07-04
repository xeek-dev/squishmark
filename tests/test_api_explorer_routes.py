"""The FastAPI API explorer must not shadow content URLs in production.

With DEBUG off, /docs, /redoc, and /openapi.json fall through to the pages
catch-all so a content repo can serve its own pages there (issue #140).
With DEBUG on, the explorer stays available for engine development.
"""

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


def test_docs_serves_content_page_in_production(fake_github, client: TestClient) -> None:
    fake_github.files["pages/docs.md"] = "---\ntitle: Docs\n---\n\n# Docs\n\nGuides live here.\n"
    resp = client.get("/docs")
    assert resp.status_code == 200
    assert "Guides live here" in resp.text


def test_docs_not_swagger_in_production(client: TestClient) -> None:
    resp = client.get("/docs")
    # No pages/docs.md in the default fixture content: the catch-all 404s,
    # but it must not be the Swagger UI page.
    assert "swagger" not in resp.text.lower()


def test_openapi_hidden_in_production(client: TestClient) -> None:
    resp = client.get("/openapi.json")
    assert resp.status_code == 404
