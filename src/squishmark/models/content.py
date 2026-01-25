"""Pydantic models for content (posts, pages, config)."""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class FrontMatter(BaseModel):
    """Frontmatter metadata extracted from markdown files."""

    title: str = "Untitled"
    date: date | None = None
    tags: list[str] = Field(default_factory=list)
    description: str = ""
    draft: bool = False
    template: str | None = None  # Custom template override

    # Allow extra fields for extensibility
    model_config = {"extra": "allow"}


class Post(BaseModel):
    """A blog post with parsed content."""

    slug: str
    title: str
    date: date | None = None
    tags: list[str] = Field(default_factory=list)
    description: str = ""
    content: str = ""  # Raw markdown
    html: str = ""  # Rendered HTML
    draft: bool = False
    template: str | None = None

    @property
    def url(self) -> str:
        """Return the URL path for this post."""
        return f"/posts/{self.slug}"


class Page(BaseModel):
    """A static page with parsed content."""

    slug: str
    title: str
    content: str = ""  # Raw markdown
    html: str = ""  # Rendered HTML
    template: str | None = None

    @property
    def url(self) -> str:
        """Return the URL path for this page."""
        return f"/{self.slug}"


class SiteConfig(BaseModel):
    """Site-wide configuration from config.yml."""

    title: str = "My Blog"
    description: str = ""
    author: str = ""
    url: str = ""


class ThemeConfig(BaseModel):
    """Theme configuration from config.yml."""

    name: str = "default"
    pygments_style: str = "monokai"


class PostsConfig(BaseModel):
    """Posts configuration from config.yml."""

    per_page: int = 10


class Config(BaseModel):
    """Full configuration from config.yml."""

    site: SiteConfig = Field(default_factory=SiteConfig)
    theme: ThemeConfig = Field(default_factory=ThemeConfig)
    posts: PostsConfig = Field(default_factory=PostsConfig)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "Config":
        """Create a Config from a dictionary, handling missing fields gracefully."""
        if data is None:
            return cls()
        return cls(**data)


class Pagination(BaseModel):
    """Pagination information for post listings."""

    page: int = 1
    per_page: int = 10
    total_items: int = 0
    total_pages: int = 0

    @property
    def has_prev(self) -> bool:
        """Check if there's a previous page."""
        return self.page > 1

    @property
    def has_next(self) -> bool:
        """Check if there's a next page."""
        return self.page < self.total_pages

    @property
    def prev_page(self) -> int | None:
        """Get the previous page number."""
        return self.page - 1 if self.has_prev else None

    @property
    def next_page(self) -> int | None:
        """Get the next page number."""
        return self.page + 1 if self.has_next else None
