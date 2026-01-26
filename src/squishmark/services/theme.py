"""Theme engine for Jinja2 template rendering."""

import asyncio
from pathlib import Path
from typing import Any

from jinja2 import BaseLoader, Environment, TemplateNotFound

from squishmark.models.content import Config, Page, Pagination, Post
from squishmark.services.github import GitHubService


class HybridLoader(BaseLoader):
    """
    Custom Jinja2 loader that supports loading templates from:
    1. Custom theme in content repository (via GitHub service)
    2. Bundled default theme (local filesystem)

    This allows theme authors to override only specific templates.
    """

    def __init__(
        self,
        github_service: GitHubService,
        default_theme_path: Path,
        custom_theme_prefix: str = "theme",
    ) -> None:
        self.github_service = github_service
        self.default_theme_path = default_theme_path
        self.custom_theme_prefix = custom_theme_prefix
        self._loop: asyncio.AbstractEventLoop | None = None

    def _get_loop(self) -> asyncio.AbstractEventLoop:
        """Get the event loop, creating one if necessary."""
        try:
            return asyncio.get_running_loop()
        except RuntimeError:
            if self._loop is None:
                self._loop = asyncio.new_event_loop()
            return self._loop

    def get_source(self, environment: Environment, template: str) -> tuple[str, str | None, Any]:
        """
        Load a template source.

        Args:
            environment: Jinja2 environment
            template: Template name (e.g., "post.html")

        Returns:
            Tuple of (source, filename, uptodate_func)
        """
        # Try custom theme first (from content repo)
        custom_path = f"{self.custom_theme_prefix}/{template}"

        # We need to run async code in sync context
        loop = self._get_loop()
        if loop.is_running():
            # We're in an async context - use a new thread
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    self.github_service.get_file(custom_path),
                )
                result = future.result()
        else:
            result = loop.run_until_complete(self.github_service.get_file(custom_path))

        if result is not None:
            # Found in custom theme
            return result.content, custom_path, lambda: False

        # Fall back to default theme
        default_path = self.default_theme_path / template
        if default_path.exists():
            return default_path.read_text(encoding="utf-8"), str(default_path), None

        raise TemplateNotFound(template)


class AsyncHybridLoader(BaseLoader):
    """
    Async-friendly template loader that caches templates in memory.
    Templates must be pre-loaded before rendering.
    """

    def __init__(self, default_theme_path: Path) -> None:
        self.default_theme_path = default_theme_path
        self._template_cache: dict[str, str] = {}

    def add_template(self, name: str, source: str) -> None:
        """Add a template to the cache."""
        self._template_cache[name] = source

    def clear_cache(self) -> None:
        """Clear the template cache."""
        self._template_cache.clear()

    def get_source(self, environment: Environment, template: str) -> tuple[str, str | None, Any]:
        """Load a template from cache or default theme."""
        # Check cache first
        if template in self._template_cache:
            return self._template_cache[template], template, lambda: True

        # Fall back to default theme
        default_path = self.default_theme_path / template
        if default_path.exists():
            return default_path.read_text(encoding="utf-8"), str(default_path), None

        raise TemplateNotFound(template)


class ThemeEngine:
    """Engine for rendering Jinja2 templates with theme support."""

    # Favicon candidates in order of preference
    FAVICON_CANDIDATES = [
        ("static/favicon.ico", "image/x-icon"),
        ("static/favicon.png", "image/png"),
        ("static/favicon.svg", "image/svg+xml"),
    ]

    def __init__(
        self,
        github_service: GitHubService,
        default_theme_path: Path | None = None,
    ) -> None:
        self.github_service = github_service

        # Default to the bundled theme
        if default_theme_path is None:
            from squishmark.config import get_settings

            settings = get_settings()
            default_theme_path = Path(settings.themes_path) / "default"
        self.default_theme_path = default_theme_path

        # Create loader and environment
        self.loader = AsyncHybridLoader(default_theme_path)
        self.env = Environment(
            loader=self.loader,
            autoescape=True,
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Add custom filters
        self._setup_filters()

        # Cached favicon URL (detected on first render)
        self._favicon_url: str | None = None
        self._favicon_checked: bool = False

    def _setup_filters(self) -> None:
        """Add custom Jinja2 filters."""

        def format_date(value: Any, fmt: str = "%B %d, %Y") -> str:
            """Format a date object."""
            if value is None:
                return ""
            if hasattr(value, "strftime"):
                return value.strftime(fmt)
            return str(value)

        self.env.filters["format_date"] = format_date

    async def detect_favicon(self) -> str | None:
        """
        Detect the favicon file in the content repository.

        Returns:
            URL path to the favicon (e.g., "/static/user/favicon.png") or None
        """
        if self._favicon_checked:
            return self._favicon_url

        self._favicon_checked = True

        for path, _content_type in self.FAVICON_CANDIDATES:
            file = await self.github_service.get_binary_file(path)
            if file:
                # Convert "static/favicon.png" to "/static/user/favicon.png"
                filename = path.replace("static/", "")
                self._favicon_url = f"/static/user/{filename}"
                return self._favicon_url

        return None

    def clear_favicon_cache(self) -> None:
        """Clear the cached favicon URL."""
        self._favicon_url = None
        self._favicon_checked = False

    async def load_custom_templates(self) -> int:
        """
        Pre-load custom templates from the content repository.

        Returns:
            Number of custom templates loaded
        """
        custom_templates = await self.github_service.list_directory("theme")
        count = 0

        for path in custom_templates:
            if path.endswith(".html"):
                file = await self.github_service.get_file(path)
                if file:
                    # Extract template name from path (e.g., "theme/post.html" -> "post.html")
                    template_name = path.split("/")[-1]
                    self.loader.add_template(template_name, file.content)
                    count += 1

        return count

    async def render(
        self,
        template_name: str,
        config: Config,
        **context: Any,
    ) -> str:
        """
        Render a template with the given context.

        Args:
            template_name: Name of the template (e.g., "post.html")
            config: Site configuration
            **context: Additional template context

        Returns:
            Rendered HTML string
        """
        template = self.env.get_template(template_name)

        # Detect favicon if not explicitly set in config
        favicon_url = config.site.favicon
        if not favicon_url:
            favicon_url = await self.detect_favicon()

        # Build the full context
        full_context = {
            "site": config.site,
            "theme": config.theme,
            "favicon_url": favicon_url,
            **context,
        }

        return template.render(**full_context)

    async def render_index(
        self,
        config: Config,
        posts: list[Post],
        pagination: Pagination,
        notes: list[Any] | None = None,
    ) -> str:
        """Render the index/home page."""
        return await self.render(
            "index.html",
            config,
            posts=posts,
            pagination=pagination,
            notes=notes or [],
        )

    async def render_post(
        self,
        config: Config,
        post: Post,
        notes: list[Any] | None = None,
    ) -> str:
        """Render a single post page."""
        template_name = post.template or "post.html"
        return await self.render(
            template_name,
            config,
            post=post,
            notes=notes or [],
        )

    async def render_page(
        self,
        config: Config,
        page: Page,
        notes: list[Any] | None = None,
    ) -> str:
        """Render a static page."""
        template_name = page.template or "page.html"
        return await self.render(
            template_name,
            config,
            page=page,
            notes=notes or [],
        )

    async def render_404(self, config: Config) -> str:
        """Render the 404 page."""
        try:
            return await self.render("404.html", config)
        except TemplateNotFound:
            # Fallback if no 404 template
            return "<h1>404 - Page Not Found</h1>"

    async def render_admin(
        self,
        config: Config,
        **context: Any,
    ) -> str:
        """Render the admin dashboard."""
        return await self.render("admin/admin.html", config, **context)


# Global theme engine instance
_theme_engine: ThemeEngine | None = None


async def get_theme_engine(github_service: GitHubService | None = None) -> ThemeEngine:
    """Get or create the global theme engine instance."""
    global _theme_engine
    if _theme_engine is None:
        if github_service is None:
            from squishmark.services.github import get_github_service

            github_service = get_github_service()
        _theme_engine = ThemeEngine(github_service)
        await _theme_engine.load_custom_templates()
    return _theme_engine


def reset_theme_engine() -> None:
    """Reset the global theme engine. Useful for testing or cache refresh."""
    global _theme_engine
    if _theme_engine:
        _theme_engine.clear_favicon_cache()
    _theme_engine = None
