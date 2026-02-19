"""Tests for post routes and draft filtering."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from squishmark.routers.posts import _is_admin
from squishmark.services.content import get_all_posts


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
    """Tests for draft filtering in get_all_posts."""

    @pytest.mark.asyncio
    async def test_get_all_posts_excludes_drafts(self):
        """get_all_posts should exclude draft posts by default."""
        from squishmark.services.markdown import MarkdownService

        mock_github = AsyncMock()
        mock_github.list_directory.return_value = [
            "posts/2026-01-01-published.md",
            "posts/2026-01-02-draft.md",
        ]
        mock_github.get_file.side_effect = [
            MagicMock(content="---\ntitle: Published\ndate: 2026-01-01\n---\nContent"),
            MagicMock(content="---\ntitle: Draft\ndate: 2026-01-02\ndraft: true\n---\nContent"),
        ]
        md = MarkdownService()

        posts = await get_all_posts(mock_github, md, include_drafts=False)

        assert len(posts) == 1
        assert posts[0].title == "Published"

    @pytest.mark.asyncio
    async def test_get_all_posts_includes_drafts_when_requested(self):
        """get_all_posts should include drafts when include_drafts=True."""
        from squishmark.services.markdown import MarkdownService

        mock_github = AsyncMock()
        mock_github.list_directory.return_value = [
            "posts/2026-01-01-published.md",
            "posts/2026-01-02-draft.md",
        ]
        mock_github.get_file.side_effect = [
            MagicMock(content="---\ntitle: Published\ndate: 2026-01-01\n---\nContent"),
            MagicMock(content="---\ntitle: Draft\ndate: 2026-01-02\ndraft: true\n---\nContent"),
        ]
        md = MarkdownService()

        posts = await get_all_posts(mock_github, md, include_drafts=True)

        assert len(posts) == 2
        titles = {p.title for p in posts}
        assert titles == {"Published", "Draft"}
