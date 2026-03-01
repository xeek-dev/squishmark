"""Tests for nav pages: visibility, ordering, filtering, and hidden page 404."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from squishmark.models.content import Config, FrontMatter, Page, ThemeConfig
from squishmark.services.markdown import MarkdownService


class TestVisibilityModel:
    """Tests for visibility Literal type on FrontMatter and Page."""

    def test_default_visibility_is_public(self):
        """FrontMatter and Page default to public visibility."""
        fm = FrontMatter()
        assert fm.visibility == "public"

        page = Page(slug="test", title="Test")
        assert page.visibility == "public"

    def test_valid_visibility_values(self):
        """All three visibility values should be accepted."""
        for value in ("public", "unlisted", "hidden"):
            fm = FrontMatter(visibility=value)
            assert fm.visibility == value

    def test_invalid_visibility_rejected(self):
        """Invalid visibility values should raise ValidationError."""
        with pytest.raises(ValidationError):
            FrontMatter(visibility="secret")

        with pytest.raises(ValidationError):
            Page(slug="test", title="Test", visibility="private")


class TestParsePage:
    """Tests for parse_page copying visibility and nav_order from frontmatter."""

    def test_parse_page_copies_visibility(self):
        """parse_page should copy visibility from frontmatter to Page."""
        md = MarkdownService()
        content = "---\ntitle: Hidden Page\nvisibility: hidden\n---\nContent"
        page = md.parse_page("pages/secret.md", content)

        assert page.visibility == "hidden"
        assert page.title == "Hidden Page"

    def test_parse_page_copies_nav_order(self):
        """parse_page should copy nav_order from frontmatter to Page."""
        md = MarkdownService()
        content = "---\ntitle: First\nnav_order: 1\n---\nContent"
        page = md.parse_page("pages/first.md", content)

        assert page.nav_order == 1

    def test_parse_page_defaults(self):
        """parse_page should default to public visibility and no nav_order."""
        md = MarkdownService()
        content = "---\ntitle: Normal\n---\nContent"
        page = md.parse_page("pages/normal.md", content)

        assert page.visibility == "public"
        assert page.nav_order is None


class TestHiddenPage404:
    """Tests for hidden pages returning 404 in the page router."""

    @pytest.mark.asyncio
    async def test_hidden_page_returns_404(self):
        """Hidden pages should raise HTTPException(404)."""
        from fastapi import HTTPException

        from squishmark.routers.pages import get_page

        mock_request = MagicMock()
        hidden_content = "---\ntitle: Secret\nvisibility: hidden\n---\nContent"

        with (
            patch("squishmark.routers.pages.get_github_service") as mock_get_github,
            patch("squishmark.routers.pages.get_theme_engine"),
        ):
            mock_github = AsyncMock()
            mock_get_github.return_value = mock_github
            mock_github.get_config.return_value = None
            mock_github.get_file.return_value = MagicMock(content=hidden_content)

            with pytest.raises(HTTPException) as exc_info:
                await get_page(mock_request, "secret")

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_unlisted_page_does_not_404(self):
        """Unlisted pages should render normally (not 404)."""
        from squishmark.routers.pages import get_page

        unlisted_content = "---\ntitle: Unlisted\nvisibility: unlisted\n---\nContent"

        with (
            patch("squishmark.routers.pages.get_github_service") as mock_get_github,
            patch("squishmark.routers.pages.get_theme_engine") as mock_get_engine,
        ):
            mock_github = AsyncMock()
            mock_get_github.return_value = mock_github
            mock_github.get_config.return_value = None
            mock_github.get_file.return_value = MagicMock(content=unlisted_content)

            mock_engine = AsyncMock()
            mock_get_engine.return_value = mock_engine
            mock_engine.render_page.return_value = "<html>Unlisted</html>"

            mock_request = MagicMock()
            response = await get_page(mock_request, "unlisted")

            assert response.status_code == 200


class TestGetNavPages:
    """Tests for ThemeEngine.get_nav_pages() filtering and sorting."""

    def _make_page_content(self, title: str, visibility: str = "public", nav_order: int | None = None) -> str:
        """Build markdown content with frontmatter."""
        lines = [f"title: {title}", f"visibility: {visibility}"]
        if nav_order is not None:
            lines.append(f"nav_order: {nav_order}")
        return "---\n" + "\n".join(lines) + "\n---\nContent"

    @pytest.mark.asyncio
    async def test_filters_public_only(self):
        """Only public pages should appear in nav."""
        from squishmark.services.theme.engine import ThemeEngine

        mock_github = AsyncMock()
        mock_github.list_directory.return_value = [
            "pages/about.md",
            "pages/secret.md",
            "pages/draft.md",
        ]
        mock_github.get_file.side_effect = [
            MagicMock(content=self._make_page_content("About", "public")),
            MagicMock(content=self._make_page_content("Secret", "hidden")),
            MagicMock(content=self._make_page_content("Draft", "unlisted")),
        ]

        engine = ThemeEngine(mock_github)
        config = Config()
        pages = await engine.get_nav_pages(config)

        assert len(pages) == 1
        assert pages[0].title == "About"

    @pytest.mark.asyncio
    async def test_sort_by_nav_order_then_title(self):
        """Pages sort by nav_order ascending (nulls last), then title."""
        from squishmark.services.theme.engine import ThemeEngine

        mock_github = AsyncMock()
        mock_github.list_directory.return_value = [
            "pages/contact.md",
            "pages/about.md",
            "pages/projects.md",
            "pages/blog.md",
        ]
        mock_github.get_file.side_effect = [
            MagicMock(content=self._make_page_content("Contact", nav_order=2)),
            MagicMock(content=self._make_page_content("About", nav_order=1)),
            MagicMock(content=self._make_page_content("Projects")),
            MagicMock(content=self._make_page_content("Blog")),
        ]

        engine = ThemeEngine(mock_github)
        config = Config()
        pages = await engine.get_nav_pages(config)

        titles = [p.title for p in pages]
        # nav_order 1, nav_order 2, then alphabetical nulls
        assert titles == ["About", "Contact", "Blog", "Projects"]

    @pytest.mark.asyncio
    async def test_nav_max_pages_truncation(self):
        """nav_max_pages should limit the number of pages returned."""
        from squishmark.services.theme.engine import ThemeEngine

        mock_github = AsyncMock()
        mock_github.list_directory.return_value = [
            "pages/a.md",
            "pages/b.md",
            "pages/c.md",
        ]
        mock_github.get_file.side_effect = [
            MagicMock(content=self._make_page_content("A")),
            MagicMock(content=self._make_page_content("B")),
            MagicMock(content=self._make_page_content("C")),
        ]

        engine = ThemeEngine(mock_github)
        config = Config(theme=ThemeConfig(nav_max_pages=2))
        pages = await engine.get_nav_pages(config)

        assert len(pages) == 2

    @pytest.mark.asyncio
    async def test_empty_list_when_no_pages(self):
        """Should return empty list when no pages exist."""
        from squishmark.services.theme.engine import ThemeEngine

        mock_github = AsyncMock()
        mock_github.list_directory.return_value = []

        engine = ThemeEngine(mock_github)
        config = Config()
        pages = await engine.get_nav_pages(config)

        assert pages == []
