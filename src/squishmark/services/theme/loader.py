"""Custom Jinja2 template loader with multi-source support."""

from pathlib import Path
from typing import Any

from jinja2 import BaseLoader, Environment, TemplateNotFound


def split_theme(name: str, default_theme: str) -> tuple[str, str]:
    """Split a theme-prefixed template name into ``(theme, template)``.

    Names are of the form ``"<theme>/<template>"`` (e.g. ``"terminal/post.html"``
    or ``"terminal/admin/admin.html"``). A name without a slash carries no theme
    prefix and resolves against the default theme.
    """
    theme, sep, rest = name.partition("/")
    if not sep:
        return default_theme, name
    return theme, rest


class ThemedEnvironment(Environment):
    """Jinja environment that keeps extends/includes within the parent's theme.

    Template names are theme-prefixed (``"<theme>/<name>"``). When a template
    references another by bare name, the reference is resolved against the
    parent's theme so inheritance stays within the requested theme. Fallback to
    the default theme is handled by :class:`AsyncHybridLoader`.
    """

    def join_path(self, template: str, parent: str) -> str:
        theme, sep, _rest = parent.partition("/")
        if not sep:
            return template
        return f"{theme}/{template}"


class AsyncHybridLoader(BaseLoader):
    """
    Async-friendly template loader that caches templates in memory.
    Templates must be pre-loaded before rendering.

    Lookup is stateless: the requested theme is encoded in the template name
    (``"<theme>/<name>"``). For each lookup the sources are searched in order:

    1. Custom templates cache (from content repo), keyed by bare name
    2. Requested theme directory
    3. Default bundled theme directory (fallback)
    """

    def __init__(self, themes_path: Path, default_theme: str = "default") -> None:
        self.themes_path = themes_path
        self.default_theme = default_theme
        self._template_cache: dict[str, str] = {}

    def add_template(self, name: str, source: str) -> None:
        """Add a template to the cache."""
        self._template_cache[name] = source

    def clear_cache(self) -> None:
        """Clear the template cache."""
        self._template_cache.clear()

    def get_source(self, environment: Environment, template: str) -> tuple[str, str | None, Any]:
        """Load a template from cache, requested theme, or default theme."""
        theme, name = split_theme(template, self.default_theme)

        # Custom templates from the content repo take precedence, keyed by their
        # bare name as loaded (see ThemeEngine.load_custom_templates).
        if name in self._template_cache:
            return self._template_cache[name], template, lambda: True

        # Requested theme directory (skipped when it is the default theme).
        # Return the prefixed name so join_path can recover the theme, and
        # lambda: False to always re-read (supports live theme editing).
        if theme != self.default_theme:
            theme_path = self.themes_path / theme / name
            if theme_path.exists():
                return theme_path.read_text(encoding="utf-8"), template, lambda: False

        # Fall back to the default theme.
        default_path = self.themes_path / self.default_theme / name
        if default_path.exists():
            return default_path.read_text(encoding="utf-8"), template, lambda: False

        raise TemplateNotFound(template)
