"""Integration tests for the /posts routes.

Driven through the real ``create_app()`` so pagination, draft gating, and the
HTML 404 handler are all exercised end to end. Content comes from the in-memory
``FakeGitHubService`` installed by the autouse fixture (five published posts,
one draft, ``per_page=2``).
"""

from fastapi.testclient import TestClient


def test_list_posts_ok_with_content(client: TestClient) -> None:
    resp = client.get("/posts")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")
    # Newest two posts are on page 1 (per_page=2, newest-first by date).
    assert "Post Five" in resp.text
    assert "Post Four" in resp.text


def test_list_posts_pagination_page_two(client: TestClient) -> None:
    resp = client.get("/posts", params={"page": 2})
    assert resp.status_code == 200
    # Page 2 shows the next slice of published posts.
    assert "Post Three" in resp.text
    assert "Post Two" in resp.text
    # Page-1 posts should not appear on page 2.
    assert "Post Five" not in resp.text


def test_list_posts_out_of_range_page_clamps(client: TestClient) -> None:
    """The handler clamps ``page`` to ``total_pages`` (posts.py:44), so an
    absurdly high page returns the last page (200), not an error."""
    resp = client.get("/posts", params={"page": 999})
    assert resp.status_code == 200
    # Five published posts / per_page=2 => 3 pages; last page holds Post One.
    assert "Post One" in resp.text


def test_drafts_absent_for_anonymous(client: TestClient) -> None:
    """Anonymous listing must never surface a draft, across all pages."""
    seen_draft = False
    for page in (1, 2, 3):
        resp = client.get("/posts", params={"page": page})
        assert resp.status_code == 200
        if "Secret Draft" in resp.text:
            seen_draft = True
    assert not seen_draft


def test_drafts_present_for_admin(admin_client: TestClient) -> None:
    """Admins see drafts in the listing (include_drafts=True). With the draft
    included there are 6 posts; the newest is the draft, so it lands on page 1."""
    resp = admin_client.get("/posts")
    assert resp.status_code == 200
    assert "Secret Draft" in resp.text


def test_get_post_ok_known_slug(client: TestClient) -> None:
    resp = client.get("/posts/post-one")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")
    assert "Post One" in resp.text


def test_get_post_404_unknown_slug(client: TestClient) -> None:
    resp = client.get("/posts/does-not-exist")
    assert resp.status_code == 404


def test_draft_detail_404_for_anonymous(client: TestClient) -> None:
    resp = client.get("/posts/secret-draft")
    assert resp.status_code == 404


def test_draft_detail_200_for_admin(admin_client: TestClient) -> None:
    resp = admin_client.get("/posts/secret-draft")
    assert resp.status_code == 200
    assert "Secret Draft" in resp.text
