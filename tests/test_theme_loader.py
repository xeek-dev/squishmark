"""Tests for the stateless theme-prefixed template loader (issue #110)."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from jinja2 import TemplateNotFound

from squishmark.models.content import Config
from squishmark.services.cache import Cache
from squishmark.services.container import Services
from squishmark.services.theme.engine import ThemeEngine
from squishmark.services.theme.loader import (
    AsyncHybridLoader,
    ThemedEnvironment,
    split_theme,
)


def _build_themes(root: Path) -> None:
    """Create a minimal three-theme tree for lookup tests.

    Only ``default`` ships ``shared.html``; ``blue-tech`` and ``terminal`` rely
    on the default-theme fallback for it.
    """
    for theme in ("default", "blue-tech", "terminal"):
        theme_dir = root / theme
        theme_dir.mkdir(parents=True)
        (theme_dir / "base.html").write_text(f"BASE:{theme}", encoding="utf-8")
        # A child that extends its own theme's base by bare name.
        (theme_dir / "child.html").write_text('{% extends "base.html" %}', encoding="utf-8")
    # shared.html only exists in the default theme.
    (root / "default" / "shared.html").write_text("SHARED:default", encoding="utf-8")


class TestSplitTheme:
    def test_prefixed_name(self):
        assert split_theme("terminal/post.html", "default") == ("terminal", "post.html")

    def test_nested_name_keeps_remainder(self):
        assert split_theme("terminal/admin/admin.html", "default") == (
            "terminal",
            "admin/admin.html",
        )

    def test_bare_name_uses_default_theme(self):
        assert split_theme("post.html", "default") == ("default", "post.html")


class TestLoaderFallbackChain:
    def test_requested_theme_wins(self, tmp_path: Path):
        _build_themes(tmp_path)
        loader = AsyncHybridLoader(tmp_path)
        source, _name, _uptodate = loader.get_source(MagicMock(), "terminal/base.html")
        assert source == "BASE:terminal"

    def test_falls_back_to_default_theme(self, tmp_path: Path):
        _build_themes(tmp_path)
        loader = AsyncHybridLoader(tmp_path)
        # terminal has no shared.html, so the default theme provides it.
        source, _name, _uptodate = loader.get_source(MagicMock(), "terminal/shared.html")
        assert source == "SHARED:default"

    def test_custom_cache_beats_theme_and_default(self, tmp_path: Path):
        _build_themes(tmp_path)
        loader = AsyncHybridLoader(tmp_path)
        loader.add_template("base.html", "CUSTOM:base")
        source, _name, _uptodate = loader.get_source(MagicMock(), "terminal/base.html")
        assert source == "CUSTOM:base"

    def test_default_theme_request_skips_theme_lookup(self, tmp_path: Path):
        _build_themes(tmp_path)
        loader = AsyncHybridLoader(tmp_path)
        source, _name, _uptodate = loader.get_source(MagicMock(), "default/base.html")
        assert source == "BASE:default"

    def test_missing_template_raises(self, tmp_path: Path):
        _build_themes(tmp_path)
        loader = AsyncHybridLoader(tmp_path)
        with pytest.raises(TemplateNotFound):
            loader.get_source(MagicMock(), "terminal/does-not-exist.html")

    def test_returned_name_is_theme_prefixed(self, tmp_path: Path):
        """The filename passed back must stay theme-prefixed so join_path can
        recover the theme for extends/includes."""
        _build_themes(tmp_path)
        loader = AsyncHybridLoader(tmp_path)
        _source, name, _uptodate = loader.get_source(MagicMock(), "terminal/base.html")
        assert name == "terminal/base.html"


class TestTraversalRejection:
    @pytest.mark.parametrize(
        "name",
        [
            "terminal/../secrets.txt",
            "terminal/../../etc/hosts",
            "../default/base.html",
            "/etc/hosts",
            "terminal//etc/hosts",
            "terminal/..\\..\\etc\\hosts",
            "..\\etc\\hosts",
        ],
    )
    def test_traversal_names_rejected(self, tmp_path: Path, name: str):
        _build_themes(tmp_path)
        loader = AsyncHybridLoader(tmp_path)
        with pytest.raises(TemplateNotFound):
            loader.get_source(MagicMock(), name)

    def test_include_traversal_rejected(self, tmp_path: Path):
        _build_themes(tmp_path)
        (tmp_path / "terminal" / "evil.html").write_text('{% include "../../secret.txt" %}', encoding="utf-8")
        (tmp_path / "secret.txt").write_text("SECRET", encoding="utf-8")
        env = ThemedEnvironment(loader=AsyncHybridLoader(tmp_path))
        with pytest.raises(TemplateNotFound):
            env.get_template("terminal/evil.html").render()

    def test_nested_names_still_resolve(self, tmp_path: Path):
        _build_themes(tmp_path)
        admin_dir = tmp_path / "terminal" / "admin"
        admin_dir.mkdir()
        (admin_dir / "admin.html").write_text("ADMIN:terminal", encoding="utf-8")
        env = ThemedEnvironment(loader=AsyncHybridLoader(tmp_path))
        assert env.get_template("terminal/admin/admin.html").render() == "ADMIN:terminal"


class TestThemedEnvironmentJoinPath:
    def test_keeps_reference_within_parent_theme(self, tmp_path: Path):
        _build_themes(tmp_path)
        env = ThemedEnvironment(loader=AsyncHybridLoader(tmp_path))
        # child.html extends "base.html"; it must resolve within its own theme.
        assert env.get_template("terminal/child.html").render() == "BASE:terminal"
        assert env.get_template("blue-tech/child.html").render() == "BASE:blue-tech"
        assert env.get_template("default/child.html").render() == "BASE:default"

    def test_bare_parent_returns_reference_unchanged(self, tmp_path: Path):
        _build_themes(tmp_path)
        env = ThemedEnvironment(loader=AsyncHybridLoader(tmp_path))
        assert env.join_path("base.html", "child.html") == "base.html"


def _make_engine(themes_path: Path) -> ThemeEngine:
    github_service = MagicMock()
    github_service.list_directory = AsyncMock(return_value=[])
    github_service.get_config = AsyncMock(return_value={})
    # get_nav_pages reaches the cached content layer through services; an empty
    # pages listing yields an empty navbar.
    services = Services(settings=MagicMock(), cache=Cache(ttl_seconds=0), github=github_service)
    engine = ThemeEngine(services, themes_path=themes_path)

    # Favicon detection is an await point in render(); yield control there so
    # concurrent renders interleave (this is where the old shared state raced).
    async def _detect() -> None:
        await asyncio.sleep(0)
        return None

    engine.favicon_detector.detect = _detect  # type: ignore[assignment]
    return engine


class TestConcurrentRenders:
    @pytest.mark.asyncio
    async def test_concurrent_theme_overrides_do_not_cross_contaminate(self, tmp_path: Path):
        """Renders with different theme overrides must resolve extends within
        their own theme even when interleaved (issue #110)."""
        _build_themes(tmp_path)
        # index.html extends base.html by bare name, exercising the loader.
        for theme in ("blue-tech", "terminal", "default"):
            (tmp_path / theme / "index.html").write_text('{% extends "base.html" %}', encoding="utf-8")
        engine = _make_engine(tmp_path)
        config = Config()

        results = await asyncio.gather(
            *[
                engine.render("index.html", config, theme_override=theme)
                for theme in ("blue-tech", "terminal", "default", "terminal", "blue-tech")
            ]
        )

        assert results == [
            "BASE:blue-tech",
            "BASE:terminal",
            "BASE:default",
            "BASE:terminal",
            "BASE:blue-tech",
        ]


class TestReload:
    @pytest.mark.asyncio
    async def test_reload_picks_up_edited_custom_template(self, tmp_path: Path):
        """reload() must serve the new custom template source, not Jinja's
        cached compile (custom templates report uptodate=True)."""
        from squishmark.services.github import GitHubFile

        _build_themes(tmp_path)
        engine = _make_engine(tmp_path)
        github = engine.github_service
        github.list_directory = AsyncMock(return_value=["theme/snippet.html"])
        github.get_file = AsyncMock(return_value=GitHubFile(path="theme/snippet.html", content="V1"))

        await engine.load_custom_templates()
        assert engine.render_partial("snippet.html", theme_override="default") == "V1"

        github.get_file = AsyncMock(return_value=GitHubFile(path="theme/snippet.html", content="V2"))
        await engine.reload()
        assert engine.render_partial("snippet.html", theme_override="default") == "V2"
        # reload must bypass the content cache, not rely on callers clearing it
        github.get_file.assert_called_with("theme/snippet.html", use_cache=False)
