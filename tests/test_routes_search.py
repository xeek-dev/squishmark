"""Integration tests for GET /search.

Driven through the real ``create_app()``; content comes from the
``FakeGitHubService`` installed by the autouse fixture (five published
posts "Post One".."Post Five" + the draft "Secret Draft"). Also guards the
draft-leak property: the cached search index is audience-separated, so an
admin search must never poison anonymous results (and vice versa).
"""

from fastapi.testclient import TestClient

RESULT_KEYS = {"title", "url", "date", "tags", "excerpt", "draft"}


def test_search_returns_json_results(client: TestClient) -> None:
    """Also proves the route isn't swallowed by the pages catch-all,
    which would return an HTML 404 instead of JSON."""
    resp = client.get("/search", params={"q": "post"})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/json")
    assert resp.headers["cache-control"] == "no-store"
    body = resp.json()
    assert body["query"] == "post"
    assert len(body["results"]) == 5
    for result in body["results"]:
        assert set(result) == RESULT_KEYS
    assert body["results"][0]["url"].startswith("/posts/")


def test_search_draft_hidden_for_anonymous(client: TestClient) -> None:
    resp = client.get("/search", params={"q": "secret"})
    assert resp.status_code == 200
    assert resp.json()["results"] == []


def test_search_draft_flagged_for_admin(admin_client: TestClient) -> None:
    resp = admin_client.get("/search", params={"q": "secret"})
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert len(results) == 1
    assert results[0]["title"] == "Secret Draft"
    assert results[0]["url"] == "/posts/secret-draft"
    assert results[0]["draft"] is True


def test_search_empty_query_returns_empty(client: TestClient) -> None:
    resp = client.get("/search")
    assert resp.status_code == 200
    assert resp.json() == {"query": "", "results": []}


def test_search_short_query_returns_empty(client: TestClient) -> None:
    resp = client.get("/search", params={"q": "p"})
    assert resp.status_code == 200
    assert resp.json()["results"] == []


def test_search_no_match_returns_empty(client: TestClient) -> None:
    resp = client.get("/search", params={"q": "zzzznomatch"})
    assert resp.status_code == 200
    assert resp.json()["results"] == []


def test_admin_search_does_not_poison_anonymous_results(
    admin_client: TestClient,
    client: TestClient,
) -> None:
    """Admin searches first (builds the drafts-included index), then an
    anonymous search must still exclude drafts."""
    admin_resp = admin_client.get("/search", params={"q": "secret"})
    assert len(admin_resp.json()["results"]) == 1

    anon_resp = client.get("/search", params={"q": "secret"})
    assert anon_resp.json()["results"] == []


def test_anonymous_search_does_not_hide_drafts_from_admin(
    client: TestClient,
    admin_client: TestClient,
) -> None:
    """Anonymous searches first (builds the published-only index), then an
    admin search must still include drafts."""
    anon_resp = client.get("/search", params={"q": "secret"})
    assert anon_resp.json()["results"] == []

    admin_resp = admin_client.get("/search", params={"q": "secret"})
    results = admin_resp.json()["results"]
    assert len(results) == 1
    assert results[0]["draft"] is True
