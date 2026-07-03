"""Service container: the app's long-lived services, built once per app.

Constructed in the FastAPI lifespan handler and hung on ``app.state`` so routes
and other dependencies resolve services via ``Depends`` (see dependencies.py)
instead of module-level singletons.
"""

from dataclasses import dataclass

from squishmark.config import Settings
from squishmark.models.content import Config
from squishmark.services.cache import Cache
from squishmark.services.github import GitHubService
from squishmark.services.livereload import LiveReloadService
from squishmark.services.markdown import MarkdownService


@dataclass
class Services:
    """Bundle of the app's shared services, passed where DI is needed."""

    settings: Settings
    cache: Cache
    github: GitHubService
    livereload: LiveReloadService | None = None
    _markdown: MarkdownService | None = None

    def markdown_for(self, config: Config) -> MarkdownService:
        """Return the markdown service, building it once from the first config.

        The pygments_style is fixed by the first config seen and reused for the
        app's life (issue #109 revisits this): behavior matches the previous
        module-global get_markdown_service.
        """
        if self._markdown is None:
            self._markdown = MarkdownService(pygments_style=config.theme.pygments_style)
        return self._markdown


def create_github_service(settings: Settings, cache: Cache) -> GitHubService:
    """Construct the GitHub content service (patched in tests to inject a fake)."""
    return GitHubService(settings, cache)


def build_services(settings: Settings) -> Services:
    """Construct the long-lived services for the app (called from the lifespan)."""
    # Debug uses a zero TTL so content edits show up immediately.
    cache = Cache(ttl_seconds=0 if settings.debug else settings.cache_ttl_seconds)
    github = create_github_service(settings, cache)
    return Services(settings=settings, cache=cache, github=github)
