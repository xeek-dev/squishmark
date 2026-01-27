"""Theme engine for Jinja2 template rendering."""

from pathlib import Path
from typing import TYPE_CHECKING, Any

from jinja2 import Environment, TemplateNotFound

from squishmark.models.content import Config, Page, Pagination, Post
from squishmark.services.theme.favicon import FaviconDetector
from squishmark.services.theme.filters import register_filters
from squishmark.services.theme.loader import AsyncHybridLoader

if TYPE_CHECKING:
    from squishmark.services.github import GitHubService


class ThemeEngine:
    """Engine for rendering Jinja2 templates with theme support."""

    def __init__(
        self,
        github_service: "GitHubService",
        themes_path: Path | None = None,
    ) -> None:
        self.github_service = github_service

        # Default to the bundled themes directory
        if themes_path is None:
            from squishmark.config import get_settings

            settings = get_settings()
            themes_path = Path(settings.resolved_themes_path)
        self.themes_path = themes_path

        # Create loader and environment
        self.loader = AsyncHybridLoader(themes_path)
        self.env = Environment(
            loader=self.loader,
            autoescape=True,
            trim_blocks=True,
            lstrip_blocks=True,
            auto_reload=True,  # Always check uptodate() to support dynamic theme switching
        )

        # Add custom filters
        register_filters(self.env)

        # Favicon detector for content repository
        self.favicon_detector = FaviconDetector(github_service)

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
        theme_override: str | None = None,
        **context: Any,
    ) -> str:
        """
        Render a template with the given context.

        Args:
            template_name: Name of the template (e.g., "post.html")
            config: Site configuration
            theme_override: Override theme name for static file paths
            **context: Additional template context

        Returns:
            Rendered HTML string
        """
        # Resolve theme name (override or config default)
        theme_name = theme_override or config.theme.name

        # Set the loader's current theme before getting template
        self.loader.current_theme = theme_name

        template = self.env.get_template(template_name)

        # Detect favicon if not explicitly set in config
        favicon_url = config.site.favicon
        if not favicon_url:
            favicon_url = await self.favicon_detector.detect()

        # Build the full context
        full_context = {
            "site": config.site,
            "theme": config.theme,
            "theme_name": theme_name,
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
        theme_override: str | None = None,
    ) -> str:
        """Render the index/home page."""
        return await self.render(
            "index.html",
            config,
            theme_override=theme_override,
            posts=posts,
            pagination=pagination,
            notes=notes or [],
        )

    async def render_post(
        self,
        config: Config,
        post: Post,
        notes: list[Any] | None = None,
        theme_override: str | None = None,
    ) -> str:
        """Render a single post page."""
        template_name = post.template or "post.html"
        # Use post's theme if set, otherwise use provided override
        resolved_theme = post.theme or theme_override
        return await self.render(
            template_name,
            config,
            theme_override=resolved_theme,
            post=post,
            notes=notes or [],
        )

    async def render_page(
        self,
        config: Config,
        page: Page,
        notes: list[Any] | None = None,
        theme_override: str | None = None,
    ) -> str:
        """Render a static page."""
        template_name = page.template or "page.html"
        # Use page's theme if set, otherwise use provided override
        resolved_theme = page.theme or theme_override
        return await self.render(
            template_name,
            config,
            theme_override=resolved_theme,
            page=page,
            notes=notes or [],
        )

    async def render_404(self, config: Config, theme_override: str | None = None) -> str:
        """Render the 404 page."""
        try:
            return await self.render("404.html", config, theme_override=theme_override)
        except TemplateNotFound:
            # Fallback if no 404 template
            return "<h1>404 - Page Not Found</h1>"

    async def render_admin(
        self,
        config: Config,
        theme_override: str | None = None,
        **context: Any,
    ) -> str:
        """Render the admin dashboard."""
        return await self.render("admin/admin.html", config, theme_override=theme_override, **context)


# Global theme engine instance
_theme_engine: ThemeEngine | None = None


async def get_theme_engine(github_service: "GitHubService | None" = None) -> ThemeEngine:
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
        _theme_engine.favicon_detector.clear_cache()
    _theme_engine = None
