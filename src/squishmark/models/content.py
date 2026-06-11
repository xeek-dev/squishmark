"""Pydantic models for content (posts, pages, config)."""

import datetime
import math
import re
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

_TOC_TRUE_STRINGS = {"true", "yes", "on", "1", "t", "y"}
_TOC_FALSE_STRINGS = {"false", "no", "off", "0", "f", "n"}


class FrontMatter(BaseModel):
    """Frontmatter metadata extracted from markdown files."""

    title: str = "Untitled"
    date: datetime.date | None = None
    tags: list[str] = Field(default_factory=list)
    description: str = ""
    draft: bool = False
    featured: bool = False
    featured_order: int | None = None  # Explicit ordering (lower = first)
    template: str | None = None  # Custom template override
    theme: str | None = None  # Per-page theme override
    author: str | None = None  # Per-content author override (used by posts)
    image: str | None = None  # Featured image URL (used for og:image)
    visibility: Literal["public", "unlisted", "hidden"] = "public"
    nav_order: int | None = None  # Explicit ordering for navbar
    toc: bool = True  # Per-post opt-out for auto-generated table of contents
    series: str | None = None  # Series/collection name this post belongs to
    series_order: int | None = None  # Position within the series (lower = first)

    # Allow extra fields for extensibility
    model_config = {"extra": "allow"}

    @field_validator("toc", mode="before")
    @classmethod
    def _coerce_toc(cls, v: Any) -> Any:
        """Coerce null / unrecognized values to the default (True).

        YAML allows ``toc: null``, ``toc:`` (empty), and arbitrary strings.
        Pydantic's strict bool parser rejects those with ValidationError,
        which would crash the whole post-loading path (a 500) for a stylistic
        frontmatter field. Default to showing the TOC and move on.
        """
        if v is None:
            return True
        if isinstance(v, bool):
            return v
        if isinstance(v, (int, float)):
            return bool(v)
        if isinstance(v, str):
            normalized = v.strip().lower()
            if normalized in _TOC_TRUE_STRINGS:
                return True
            if normalized in _TOC_FALSE_STRINGS:
                return False
        return True  # unrecognized type/value — fall back to default

    @field_validator("series_order", mode="before")
    @classmethod
    def _coerce_series_order(cls, v: Any) -> Any:
        """Coerce null / empty / malformed values to None.

        YAML allows ``series_order: null``, ``series_order:`` (empty), and
        arbitrary strings. Pydantic's strict int parser rejects non-numeric
        strings with ValidationError, which would crash the post-loading path
        (a 500) for a stylistic frontmatter field. Treat anything that isn't a
        clean integer as "unordered" (None) and move on.
        """
        if v is None or v == "":
            return None
        if isinstance(v, bool):
            return None  # bool is an int subclass; reject True/False as garbage
        if isinstance(v, int):
            return v
        if isinstance(v, float):
            # YAML parses `.nan` / `.inf` to non-finite floats; int() on those
            # raises (ValueError/OverflowError) — treat them as garbage.
            return int(v) if math.isfinite(v) else None
        if isinstance(v, str):
            stripped = v.strip()
            try:
                return int(stripped)
            except ValueError:
                return None
        return None  # unrecognized type/value — treat as unordered


class Post(BaseModel):
    """A blog post with parsed content."""

    slug: str
    title: str
    date: datetime.date | None = None
    tags: list[str] = Field(default_factory=list)
    description: str = ""
    content: str = ""  # Raw markdown
    html: str = ""  # Rendered HTML
    toc: str = ""  # Rendered TOC fragment (HTML); empty when disabled or no headings
    draft: bool = False
    featured: bool = False
    featured_order: int | None = None  # Explicit ordering (lower = first)
    template: str | None = None
    theme: str | None = None  # Per-page theme override
    author: str | None = None  # Per-post author override
    image: str | None = None  # Featured image URL (used for og:image)
    series: str | None = None  # Series/collection name this post belongs to
    series_order: int | None = None  # Position within the series (lower = first)

    @property
    def url(self) -> str:
        """Return the URL path for this post."""
        return f"/posts/{self.slug}"

    @property
    def reading_time(self) -> str:
        """Estimate reading time based on word count (~238 WPM)."""
        # Strip markdown/HTML artifacts for a rough word count
        text = re.sub(r"<[^>]+>", "", self.html) if self.html else self.content
        if not text.strip():
            return ""
        word_count = len(text.split())
        minutes = max(1, round(word_count / 238))
        return f"{minutes} min read"


class Page(BaseModel):
    """A static page with parsed content."""

    slug: str
    title: str
    date: datetime.date | None = None
    description: str = ""
    content: str = ""  # Raw markdown
    html: str = ""  # Rendered HTML
    featured: bool = False
    featured_order: int | None = None  # Explicit ordering (lower = first)
    template: str | None = None
    theme: str | None = None  # Per-page theme override
    image: str | None = None  # Featured image URL (used for og:image)
    visibility: Literal["public", "unlisted", "hidden"] = "public"
    nav_order: int | None = None  # Explicit ordering for navbar

    @property
    def url(self) -> str:
        """Return the URL path for this page."""
        return f"/{self.slug}"


class SiteConfig(BaseModel):
    """Site-wide configuration from config.yml."""

    title: str = "My Blog"
    tagline: str | None = None  # Short subtitle shown inline next to site title in nav (with separator)
    logo: str | None = None  # Logo image URL, replaces text title if set
    description: str = ""
    author: str = ""
    url: str = ""
    favicon: str | None = None  # Custom favicon URL, e.g., "/static/user/custom-icon.png"
    featured_max: int = Field(default=5, ge=0)  # Maximum number of featured posts returned


class ThemeConfig(BaseModel):
    """Theme configuration from config.yml."""

    name: str = "default"
    pygments_style: str = "github-dark"
    background: str | None = None
    nav_image: str | None = None
    hero_image: str | None = None
    nav_max_pages: int | None = None  # Max pages shown in navbar

    # Allow extra fields for extensibility
    model_config = {"extra": "allow"}


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
