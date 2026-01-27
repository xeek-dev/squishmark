"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_themes_path() -> str:
    """Compute default themes path, checking multiple locations."""
    # Try development path first (relative to package source)
    package_dir = Path(__file__).parent
    dev_path = package_dir.parent.parent / "themes"
    if dev_path.exists():
        return str(dev_path.resolve())

    # Fall back to Docker path
    docker_path = Path("/app/themes")
    if docker_path.exists():
        return str(docker_path)

    # Last resort: return dev path (will error with clear message)
    return str(dev_path.resolve())


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # GitHub content configuration
    github_content_repo: str = ""
    github_token: str | None = None
    github_client_id: str | None = None
    github_client_secret: str | None = None
    github_webhook_secret: str | None = None

    # Admin configuration
    admin_users: str = ""  # Comma-separated GitHub usernames

    # Security
    secret_key: str = "change-me-in-production"

    # Database
    database_url: str = "sqlite+aiosqlite:////data/squishmark.db"

    # Cache
    cache_ttl_seconds: int = 300

    # Theme path - defaults to themes/ relative to package, can be overridden
    themes_path: str = ""

    # Debug mode
    debug: bool = False

    @property
    def admin_users_list(self) -> list[str]:
        """Return admin users as a list."""
        if not self.admin_users:
            return []
        return [u.strip() for u in self.admin_users.split(",") if u.strip()]

    @property
    def is_local_content(self) -> bool:
        """Check if content is loaded from local filesystem."""
        return self.github_content_repo.startswith("file://")

    @property
    def resolved_themes_path(self) -> str:
        """Return themes path, using computed default if not set."""
        if self.themes_path:
            return self.themes_path
        return _default_themes_path()


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
