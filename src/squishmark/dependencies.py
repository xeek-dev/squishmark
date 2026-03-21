"""FastAPI dependency injection utilities."""

from typing import Annotated

from fastapi import Depends, Request

from squishmark.config import Settings, get_settings

# Type alias for settings dependency
SettingsDep = Annotated[Settings, Depends(get_settings)]


def is_admin(request: Request) -> bool:
    """Check if the current user is an admin without requiring auth."""
    settings = get_settings()
    if settings.debug and settings.dev_skip_auth:
        return True
    user = request.session.get("user") if hasattr(request, "session") else None
    if user is None:
        return False
    return user.get("login") in settings.admin_users_list
