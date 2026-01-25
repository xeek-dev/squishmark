"""Application configuration using Pydantic Settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


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
    database_url: str = "sqlite+aiosqlite:///data/squishmark.db"

    # Cache
    cache_ttl_seconds: int = 300

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


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
