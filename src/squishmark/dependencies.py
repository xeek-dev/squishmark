"""FastAPI dependency injection utilities."""

import logging
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, Request

from squishmark.config import Settings, get_settings
from squishmark.models.content import Config
from squishmark.services.container import Services
from squishmark.services.markdown import MarkdownService
from squishmark.services.theme import ThemeEngine

logger = logging.getLogger(__name__)

# Type alias for settings dependency
SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_services(request: Request) -> Services:
    """Return the service container built in the lifespan and hung on app.state."""
    return request.app.state.services


ServicesDep = Annotated[Services, Depends(get_services)]


@dataclass
class SiteContext:
    """Per-request site context: the parsed config plus the services bundle.

    Folds the config-fetch ritual (``get_config`` + ``Config.from_dict``) that
    most routes repeat into one dependency. The markdown service is exposed
    lazily so config-only routes never build it.
    """

    config: Config
    services: Services

    @property
    def markdown(self) -> MarkdownService:
        """Return the markdown service for this request's config.

        Caching lives in ``Services.markdown_for``; see it for how config
        changes affect the instance.
        """
        return self.services.markdown_for(self.config)


async def get_site_context(services: ServicesDep) -> SiteContext:
    """Fetch and parse the site config, pairing it with the services bundle."""
    config_data = await services.github.get_config()
    return SiteContext(config=Config.from_dict(config_data), services=services)


SiteContextDep = Annotated[SiteContext, Depends(get_site_context)]


def get_theme_engine(request: Request) -> ThemeEngine:
    """Return the theme engine built in the lifespan and hung on app.state."""
    return request.app.state.theme_engine


ThemeEngineDep = Annotated[ThemeEngine, Depends(get_theme_engine)]


def is_admin(request: Request) -> bool:
    """Check if the current user is an admin without requiring auth."""
    settings = get_settings()
    if settings.debug and settings.dev_skip_auth:
        return True
    user = request.session.get("user") if hasattr(request, "session") else None
    if user is None:
        return False
    return user.get("login") in settings.admin_users_list


def is_htmx(request: Request) -> bool:
    """Return True when the request was made by HTMX."""
    return request.headers.get("HX-Request") == "true"


async def get_current_admin(request: Request) -> str:
    """
    Get the current admin user from session.

    Raises HTTPException 401 if not authenticated.
    Raises HTTPException 403 if not an admin.

    For HTMX requests, attaches an ``HX-Redirect`` header so the browser
    is redirected to the login page without any client JavaScript.
    """
    settings = get_settings()

    # Dev mode auth bypass (requires both flags)
    if settings.debug and settings.dev_skip_auth:
        logger.warning("Auth bypassed - returning dev-admin user")
        return "dev-admin"

    htmx_headers = {"HX-Redirect": "/auth/login"} if is_htmx(request) else None

    # Check for user in session (set by OAuth callback)
    user = request.session.get("user") if hasattr(request, "session") else None

    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated", headers=htmx_headers)

    if user["login"] not in settings.admin_users_list:
        raise HTTPException(status_code=403, detail="Not authorized", headers=htmx_headers)

    return user["login"]


AdminUser = Annotated[str, Depends(get_current_admin)]
