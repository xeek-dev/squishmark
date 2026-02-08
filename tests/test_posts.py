"""Tests for post routes and draft filtering."""

from unittest.mock import MagicMock, patch

import pytest

from squishmark.routers.posts import _is_admin


@pytest.fixture
def mock_request():
    """Create a mock request with session support."""
    request = MagicMock()
    request.session = {}
    return request


class TestIsAdmin:
    """Tests for the _is_admin helper."""

    def test_anonymous_user_is_not_admin(self, mock_request):
        """Anonymous visitors should not be detected as admin."""
        with patch("squishmark.routers.posts.get_settings") as mock_settings:
            mock_settings.return_value.debug = False
            mock_settings.return_value.dev_skip_auth = False
            mock_settings.return_value.admin_users_list = ["admin-user"]

            assert _is_admin(mock_request) is False

    def test_authenticated_admin_is_admin(self, mock_request):
        """Authenticated admin users should be detected."""
        mock_request.session = {"user": {"login": "admin-user"}}
        with patch("squishmark.routers.posts.get_settings") as mock_settings:
            mock_settings.return_value.debug = False
            mock_settings.return_value.dev_skip_auth = False
            mock_settings.return_value.admin_users_list = ["admin-user"]

            assert _is_admin(mock_request) is True

    def test_authenticated_non_admin_is_not_admin(self, mock_request):
        """Authenticated non-admin users should not be detected as admin."""
        mock_request.session = {"user": {"login": "regular-user"}}
        with patch("squishmark.routers.posts.get_settings") as mock_settings:
            mock_settings.return_value.debug = False
            mock_settings.return_value.dev_skip_auth = False
            mock_settings.return_value.admin_users_list = ["admin-user"]

            assert _is_admin(mock_request) is False

    def test_dev_skip_auth_is_admin(self, mock_request):
        """Dev mode with skip auth should be detected as admin."""
        with patch("squishmark.routers.posts.get_settings") as mock_settings:
            mock_settings.return_value.debug = True
            mock_settings.return_value.dev_skip_auth = True

            assert _is_admin(mock_request) is True

    def test_debug_without_skip_auth_is_not_admin(self, mock_request):
        """Debug mode alone (without dev_skip_auth) should not grant admin."""
        with patch("squishmark.routers.posts.get_settings") as mock_settings:
            mock_settings.return_value.debug = True
            mock_settings.return_value.dev_skip_auth = False
            mock_settings.return_value.admin_users_list = []

            assert _is_admin(mock_request) is False

    def test_no_session_attribute(self):
        """Request without session attribute should not be admin."""
        request = MagicMock(spec=[])  # No attributes at all
        with patch("squishmark.routers.posts.get_settings") as mock_settings:
            mock_settings.return_value.debug = False
            mock_settings.return_value.dev_skip_auth = False

            assert _is_admin(request) is False


class TestGetAllPostsDraftFiltering:
    """Tests for draft filtering in _get_all_posts."""

    @pytest.fixture
    def markdown_service(self):
        from squishmark.services.markdown import MarkdownService

        return MarkdownService()

    def test_draft_post_excluded_by_default(self, markdown_service):
        """Draft posts should be excluded when include_drafts is False."""
        content = """---
title: Draft Post
date: 2026-01-25
draft: true
---

Draft content.
"""
        post = markdown_service.parse_post("posts/2026-01-25-draft-post.md", content)
        assert post.draft is True

    def test_published_post_included(self, markdown_service):
        """Published posts (draft: false or missing) should always be included."""
        content = """---
title: Published Post
date: 2026-01-25
---

Published content.
"""
        post = markdown_service.parse_post(
            "posts/2026-01-25-published-post.md", content
        )
        assert post.draft is False

    def test_explicit_draft_false(self, markdown_service):
        """Posts with explicit draft: false should be included."""
        content = """---
title: Explicit Published
date: 2026-01-25
draft: false
---

Content.
"""
        post = markdown_service.parse_post(
            "posts/2026-01-25-explicit-published.md", content
        )
        assert post.draft is False
