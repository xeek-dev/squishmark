"""Custom Jinja2 template loader with multi-source support."""

from pathlib import Path
from typing import Any

from jinja2 import BaseLoader, Environment, TemplateNotFound


class AsyncHybridLoader(BaseLoader):
    """
    Async-friendly template loader that caches templates in memory.
    Templates must be pre-loaded before rendering.

    Supports loading from:
    1. Custom templates cache (from content repo)
    2. Current bundled theme directory
    3. Default bundled theme directory (fallback)
    """

    def __init__(self, themes_path: Path, default_theme: str = "default") -> None:
        self.themes_path = themes_path
        self.default_theme = default_theme
        self._current_theme: str = default_theme
        self._template_cache: dict[str, str] = {}

    @property
    def current_theme(self) -> str:
        """Get the current theme name."""
        return self._current_theme

    @current_theme.setter
    def current_theme(self, value: str) -> None:
        """Set the current theme name."""
        self._current_theme = value

    def add_template(self, name: str, source: str) -> None:
        """Add a template to the cache."""
        self._template_cache[name] = source

    def clear_cache(self) -> None:
        """Clear the template cache."""
        self._template_cache.clear()

    def get_source(self, environment: Environment, template: str) -> tuple[str, str | None, Any]:
        """Load a template from cache, current theme, or default theme."""
        # Check cache first (custom templates from content repo)
        if template in self._template_cache:
            return self._template_cache[template], template, lambda: True

        # Try current theme directory
        if self._current_theme != self.default_theme:
            current_path = self.themes_path / self._current_theme / template
            if current_path.exists():
                # Return lambda: False to force reload when theme changes
                return current_path.read_text(encoding="utf-8"), str(current_path), lambda: False

        # Fall back to default theme
        default_path = self.themes_path / self.default_theme / template
        if default_path.exists():
            # Return lambda: False to force reload when theme changes
            return default_path.read_text(encoding="utf-8"), str(default_path), lambda: False

        raise TemplateNotFound(template)
