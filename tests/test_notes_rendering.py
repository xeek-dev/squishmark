"""Tests for notes rendering on posts and pages."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

POST_CONTENT = "---\ntitle: Test Post\ndate: 2026-01-01\n---\nContent"
PAGE_CONTENT = "---\ntitle: About\n---\nContent"


def _admin_request():
    """Create a mock request for an authenticated admin."""
    request = MagicMock()
    request.session = {"user": {"login": "admin-user"}}
    return request


def _anonymous_request():
    """Create a mock request for an anonymous visitor."""
    request = MagicMock()
    request.session = {}
    return request


class TestPostNotesRendering:
    """Tests for notes being fetched and passed to templates on post pages."""

    @pytest.mark.asyncio
    async def test_notes_fetched_with_correct_path(self):
        """NotesService should be called with /posts/{slug} path."""
        from squishmark.routers.posts import get_post

        mock_notes = AsyncMock()
        mock_notes.get_for_path.return_value = []

        with (
            patch("squishmark.routers.posts.get_github_service") as mock_get_github,
            patch("squishmark.routers.posts.get_theme_engine") as mock_get_engine,
            patch("squishmark.routers.posts.NotesService") as mock_notes_cls,
            patch("squishmark.routers.posts.is_admin", return_value=False),
        ):
            mock_github = AsyncMock()
            mock_get_github.return_value = mock_github
            mock_github.get_config.return_value = None
            mock_github.list_directory.return_value = ["posts/2026-01-01-my-post.md"]
            mock_github.get_file.return_value = MagicMock(content=POST_CONTENT)
            mock_notes_cls.return_value = mock_notes
            mock_get_engine.return_value = AsyncMock(render_post=AsyncMock(return_value="<html></html>"))

            await get_post(_anonymous_request(), "my-post", db=AsyncMock())

            mock_notes.get_for_path.assert_called_once_with("/posts/my-post", include_private=False)

    @pytest.mark.asyncio
    async def test_admin_sees_private_notes(self):
        """Admin requests should fetch private notes (include_private=True)."""
        from squishmark.routers.posts import get_post

        mock_notes = AsyncMock()
        mock_notes.get_for_path.return_value = []

        with (
            patch("squishmark.routers.posts.get_github_service") as mock_get_github,
            patch("squishmark.routers.posts.get_theme_engine") as mock_get_engine,
            patch("squishmark.routers.posts.NotesService") as mock_notes_cls,
            patch("squishmark.routers.posts.is_admin", return_value=True),
        ):
            mock_github = AsyncMock()
            mock_get_github.return_value = mock_github
            mock_github.get_config.return_value = None
            mock_github.list_directory.return_value = ["posts/2026-01-01-my-post.md"]
            mock_github.get_file.return_value = MagicMock(content=POST_CONTENT)
            mock_notes_cls.return_value = mock_notes
            mock_get_engine.return_value = AsyncMock(render_post=AsyncMock(return_value="<html></html>"))

            await get_post(_admin_request(), "my-post", db=AsyncMock())

            mock_notes.get_for_path.assert_called_once_with("/posts/my-post", include_private=True)

    @pytest.mark.asyncio
    async def test_anonymous_cannot_see_private_notes(self):
        """Anonymous requests should not fetch private notes."""
        from squishmark.routers.posts import get_post

        mock_notes = AsyncMock()
        mock_notes.get_for_path.return_value = []

        with (
            patch("squishmark.routers.posts.get_github_service") as mock_get_github,
            patch("squishmark.routers.posts.get_theme_engine") as mock_get_engine,
            patch("squishmark.routers.posts.NotesService") as mock_notes_cls,
            patch("squishmark.routers.posts.is_admin", return_value=False),
        ):
            mock_github = AsyncMock()
            mock_get_github.return_value = mock_github
            mock_github.get_config.return_value = None
            mock_github.list_directory.return_value = ["posts/2026-01-01-my-post.md"]
            mock_github.get_file.return_value = MagicMock(content=POST_CONTENT)
            mock_notes_cls.return_value = mock_notes
            mock_get_engine.return_value = AsyncMock(render_post=AsyncMock(return_value="<html></html>"))

            await get_post(_anonymous_request(), "my-post", db=AsyncMock())

            mock_notes.get_for_path.assert_called_once_with("/posts/my-post", include_private=False)

    @pytest.mark.asyncio
    async def test_notes_passed_to_template(self):
        """Fetched notes should be passed to render_post."""
        from squishmark.routers.posts import get_post

        fake_notes = [MagicMock(text="Note 1"), MagicMock(text="Note 2")]
        mock_notes = AsyncMock()
        mock_notes.get_for_path.return_value = fake_notes

        with (
            patch("squishmark.routers.posts.get_github_service") as mock_get_github,
            patch("squishmark.routers.posts.get_theme_engine") as mock_get_engine,
            patch("squishmark.routers.posts.NotesService") as mock_notes_cls,
            patch("squishmark.routers.posts.is_admin", return_value=False),
        ):
            mock_github = AsyncMock()
            mock_get_github.return_value = mock_github
            mock_github.get_config.return_value = None
            mock_github.list_directory.return_value = ["posts/2026-01-01-my-post.md"]
            mock_github.get_file.return_value = MagicMock(content=POST_CONTENT)
            mock_notes_cls.return_value = mock_notes

            mock_engine = AsyncMock()
            mock_get_engine.return_value = mock_engine
            mock_engine.render_post.return_value = "<html></html>"

            await get_post(_anonymous_request(), "my-post", db=AsyncMock())

            # Verify notes were passed as the third positional arg to render_post
            call_args = mock_engine.render_post.call_args
            assert call_args[0][2] == fake_notes

    @pytest.mark.asyncio
    async def test_no_notes_renders_fine(self):
        """Post with no notes should render without error."""
        from squishmark.routers.posts import get_post

        mock_notes = AsyncMock()
        mock_notes.get_for_path.return_value = []

        with (
            patch("squishmark.routers.posts.get_github_service") as mock_get_github,
            patch("squishmark.routers.posts.get_theme_engine") as mock_get_engine,
            patch("squishmark.routers.posts.NotesService") as mock_notes_cls,
            patch("squishmark.routers.posts.is_admin", return_value=False),
        ):
            mock_github = AsyncMock()
            mock_get_github.return_value = mock_github
            mock_github.get_config.return_value = None
            mock_github.list_directory.return_value = ["posts/2026-01-01-my-post.md"]
            mock_github.get_file.return_value = MagicMock(content=POST_CONTENT)
            mock_notes_cls.return_value = mock_notes
            mock_get_engine.return_value = AsyncMock(render_post=AsyncMock(return_value="<html></html>"))

            response = await get_post(_anonymous_request(), "my-post", db=AsyncMock())

            assert response.status_code == 200
            call_args = mock_get_engine.return_value.render_post.call_args
            assert call_args[0][2] == []


class TestPageNotesRendering:
    """Tests for notes being fetched and passed to templates on static pages."""

    @pytest.mark.asyncio
    async def test_notes_fetched_with_correct_path(self):
        """NotesService should be called with /{slug} path."""
        from squishmark.routers.pages import get_page

        mock_notes = AsyncMock()
        mock_notes.get_for_path.return_value = []

        with (
            patch("squishmark.routers.pages.get_github_service") as mock_get_github,
            patch("squishmark.routers.pages.get_theme_engine") as mock_get_engine,
            patch("squishmark.routers.pages.NotesService") as mock_notes_cls,
            patch("squishmark.routers.pages.is_admin", return_value=False),
        ):
            mock_github = AsyncMock()
            mock_get_github.return_value = mock_github
            mock_github.get_config.return_value = None
            mock_github.get_file.return_value = MagicMock(content=PAGE_CONTENT)
            mock_notes_cls.return_value = mock_notes
            mock_get_engine.return_value = AsyncMock(render_page=AsyncMock(return_value="<html></html>"))

            await get_page(_anonymous_request(), "about", db=AsyncMock())

            mock_notes.get_for_path.assert_called_once_with("/about", include_private=False)

    @pytest.mark.asyncio
    async def test_admin_sees_private_notes(self):
        """Admin requests should fetch private notes (include_private=True)."""
        from squishmark.routers.pages import get_page

        mock_notes = AsyncMock()
        mock_notes.get_for_path.return_value = []

        with (
            patch("squishmark.routers.pages.get_github_service") as mock_get_github,
            patch("squishmark.routers.pages.get_theme_engine") as mock_get_engine,
            patch("squishmark.routers.pages.NotesService") as mock_notes_cls,
            patch("squishmark.routers.pages.is_admin", return_value=True),
        ):
            mock_github = AsyncMock()
            mock_get_github.return_value = mock_github
            mock_github.get_config.return_value = None
            mock_github.get_file.return_value = MagicMock(content=PAGE_CONTENT)
            mock_notes_cls.return_value = mock_notes
            mock_get_engine.return_value = AsyncMock(render_page=AsyncMock(return_value="<html></html>"))

            await get_page(_admin_request(), "about", db=AsyncMock())

            mock_notes.get_for_path.assert_called_once_with("/about", include_private=True)

    @pytest.mark.asyncio
    async def test_anonymous_cannot_see_private_notes(self):
        """Anonymous requests should not fetch private notes."""
        from squishmark.routers.pages import get_page

        mock_notes = AsyncMock()
        mock_notes.get_for_path.return_value = []

        with (
            patch("squishmark.routers.pages.get_github_service") as mock_get_github,
            patch("squishmark.routers.pages.get_theme_engine") as mock_get_engine,
            patch("squishmark.routers.pages.NotesService") as mock_notes_cls,
            patch("squishmark.routers.pages.is_admin", return_value=False),
        ):
            mock_github = AsyncMock()
            mock_get_github.return_value = mock_github
            mock_github.get_config.return_value = None
            mock_github.get_file.return_value = MagicMock(content=PAGE_CONTENT)
            mock_notes_cls.return_value = mock_notes
            mock_get_engine.return_value = AsyncMock(render_page=AsyncMock(return_value="<html></html>"))

            await get_page(_anonymous_request(), "about", db=AsyncMock())

            mock_notes.get_for_path.assert_called_once_with("/about", include_private=False)

    @pytest.mark.asyncio
    async def test_notes_passed_to_template(self):
        """Fetched notes should be passed to render_page."""
        from squishmark.routers.pages import get_page

        fake_notes = [MagicMock(text="Correction")]
        mock_notes = AsyncMock()
        mock_notes.get_for_path.return_value = fake_notes

        with (
            patch("squishmark.routers.pages.get_github_service") as mock_get_github,
            patch("squishmark.routers.pages.get_theme_engine") as mock_get_engine,
            patch("squishmark.routers.pages.NotesService") as mock_notes_cls,
            patch("squishmark.routers.pages.is_admin", return_value=False),
        ):
            mock_github = AsyncMock()
            mock_get_github.return_value = mock_github
            mock_github.get_config.return_value = None
            mock_github.get_file.return_value = MagicMock(content=PAGE_CONTENT)
            mock_notes_cls.return_value = mock_notes

            mock_engine = AsyncMock()
            mock_get_engine.return_value = mock_engine
            mock_engine.render_page.return_value = "<html></html>"

            await get_page(_anonymous_request(), "about", db=AsyncMock())

            call_args = mock_engine.render_page.call_args
            assert call_args[0][2] == fake_notes

    @pytest.mark.asyncio
    async def test_no_notes_renders_fine(self):
        """Page with no notes should render without error."""
        from squishmark.routers.pages import get_page

        mock_notes = AsyncMock()
        mock_notes.get_for_path.return_value = []

        with (
            patch("squishmark.routers.pages.get_github_service") as mock_get_github,
            patch("squishmark.routers.pages.get_theme_engine") as mock_get_engine,
            patch("squishmark.routers.pages.NotesService") as mock_notes_cls,
            patch("squishmark.routers.pages.is_admin", return_value=False),
        ):
            mock_github = AsyncMock()
            mock_get_github.return_value = mock_github
            mock_github.get_config.return_value = None
            mock_github.get_file.return_value = MagicMock(content=PAGE_CONTENT)
            mock_notes_cls.return_value = mock_notes
            mock_get_engine.return_value = AsyncMock(render_page=AsyncMock(return_value="<html></html>"))

            response = await get_page(_anonymous_request(), "about", db=AsyncMock())

            assert response.status_code == 200
            call_args = mock_get_engine.return_value.render_page.call_args
            assert call_args[0][2] == []
