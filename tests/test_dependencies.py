"""Tests for the SiteContext request dependency."""

from unittest.mock import AsyncMock, MagicMock

from squishmark.dependencies import SiteContext, get_site_context
from squishmark.models.content import Config
from squishmark.services.cache import Cache
from squishmark.services.container import Services
from squishmark.services.markdown import MarkdownService


def _services(config: dict) -> Services:
    github = MagicMock()
    github.get_config = AsyncMock(return_value=config)
    return Services(settings=MagicMock(), cache=Cache(ttl_seconds=0), github=github)


async def test_get_site_context_parses_config() -> None:
    services = _services({"site": {"title": "Test Blog"}})

    context = await get_site_context(services)

    assert isinstance(context, SiteContext)
    assert isinstance(context.config, Config)
    assert context.config.site.title == "Test Blog"
    assert context.services is services
    services.github.get_config.assert_awaited_once()


async def test_site_context_markdown_is_lazy_and_cached() -> None:
    services = _services({"site": {"title": "Test Blog"}})
    context = await get_site_context(services)

    md = context.markdown
    assert isinstance(md, MarkdownService)
    # The property delegates to Services.markdown_for, which caches the instance.
    assert context.markdown is md
