"""Markdown parsing and rendering service."""

import datetime
import re
from typing import Any

import markdown
from markdown.extensions.codehilite import CodeHiliteExtension
from markdown.extensions.fenced_code import FencedCodeExtension
from markdown.extensions.toc import TocExtension
from pygments.formatters import HtmlFormatter

from squishmark.models.content import Config, FrontMatter, Page, Post
from squishmark.services.url_rewriter import rewrite_image_urls


class LabeledFormatter(HtmlFormatter):
    """Displays language labels on code blocks using Pygments' filename feature."""

    def __init__(self, **options: Any) -> None:
        lang_str = options.pop("lang_str", "")
        lang = lang_str.replace("language-", "") if lang_str else ""
        if lang and lang != "text":
            options["filename"] = lang
        super().__init__(**options)


class MarkdownService:
    """Service for parsing and rendering markdown content."""

    FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

    def __init__(self, pygments_style: str = "monokai") -> None:
        self.pygments_style = pygments_style
        self._md: markdown.Markdown | None = None

    def _get_markdown_instance(self) -> markdown.Markdown:
        """Get or create the markdown instance with extensions."""
        if self._md is None:
            self._md = markdown.Markdown(
                extensions=[
                    "extra",  # Tables, footnotes, attr_list, etc.
                    FencedCodeExtension(),
                    CodeHiliteExtension(
                        css_class="highlight",
                        linenums=False,
                        guess_lang=False,
                        pygments_formatter=LabeledFormatter,
                    ),
                    TocExtension(permalink="#"),
                    "smarty",  # Smart quotes
                    "nl2br",  # Newlines to <br>
                ],
                output_format="html",
            )
        return self._md

    def parse_frontmatter(self, content: str) -> tuple[FrontMatter, str]:
        """
        Parse YAML frontmatter from markdown content.

        Args:
            content: Raw markdown content with optional frontmatter

        Returns:
            Tuple of (FrontMatter, remaining content)
        """
        import yaml

        match = self.FRONTMATTER_PATTERN.match(content)

        if not match:
            return FrontMatter(), content

        yaml_content = match.group(1)
        remaining_content = content[match.end() :]

        try:
            data = yaml.safe_load(yaml_content) or {}
            if not isinstance(data, dict):
                return FrontMatter(), remaining_content

            # Convert date string to date object if needed
            if "date" in data and isinstance(data["date"], str):
                try:
                    data["date"] = datetime.date.fromisoformat(data["date"])
                except ValueError:
                    del data["date"]

            return FrontMatter(**data), remaining_content
        except yaml.YAMLError:
            return FrontMatter(), remaining_content

    def render_markdown(self, content: str) -> str:
        """
        Render markdown content to HTML.

        Args:
            content: Markdown content (without frontmatter)

        Returns:
            Rendered HTML string
        """
        md = self._get_markdown_instance()
        md.reset()
        return md.convert(content)

    def get_pygments_css(self) -> str:
        """Generate Pygments CSS for the configured style."""
        formatter = HtmlFormatter(style=self.pygments_style)
        return formatter.get_style_defs(".highlight")

    def parse_post(self, path: str, content: str) -> Post:
        """
        Parse a post file into a Post object.

        Args:
            path: File path (used to extract slug)
            content: Raw file content with frontmatter

        Returns:
            Parsed Post object
        """
        frontmatter, markdown_content = self.parse_frontmatter(content)
        html = self.render_markdown(markdown_content)
        html = rewrite_image_urls(html, path)

        # Extract slug from path (e.g., "posts/2026-01-15-hello-world.md" -> "hello-world")
        slug = self._extract_slug(path)

        # Try to extract date from filename if not in frontmatter
        file_date = frontmatter.date
        if file_date is None:
            file_date = self._extract_date_from_path(path)

        return Post(
            slug=slug,
            title=frontmatter.title,
            date=file_date,
            tags=frontmatter.tags,
            description=frontmatter.description,
            content=markdown_content,
            html=html,
            draft=frontmatter.draft,
            featured=frontmatter.featured,
            featured_order=frontmatter.featured_order,
            template=frontmatter.template,
            theme=frontmatter.theme,
            author=frontmatter.author,
        )

    def parse_page(self, path: str, content: str) -> Page:
        """
        Parse a page file into a Page object.

        Args:
            path: File path (used to extract slug)
            content: Raw file content with frontmatter

        Returns:
            Parsed Page object
        """
        frontmatter, markdown_content = self.parse_frontmatter(content)
        html = self.render_markdown(markdown_content)
        html = rewrite_image_urls(html, path)

        # Extract slug from path (e.g., "pages/about.md" -> "about")
        slug = self._extract_slug(path, strip_date=False)

        return Page(
            slug=slug,
            title=frontmatter.title,
            content=markdown_content,
            html=html,
            featured=frontmatter.featured,
            featured_order=frontmatter.featured_order,
            template=frontmatter.template,
            theme=frontmatter.theme,
        )

    def _extract_slug(self, path: str, strip_date: bool = True) -> str:
        """Extract slug from a file path."""
        # Get filename without extension
        filename = path.split("/")[-1]
        if filename.endswith(".md"):
            filename = filename[:-3]

        if strip_date:
            # Remove date prefix if present (YYYY-MM-DD-)
            date_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}-")
            filename = date_pattern.sub("", filename)

        return filename

    def _extract_date_from_path(self, path: str) -> datetime.date | None:
        """Extract date from filename if present."""
        filename = path.split("/")[-1]
        date_pattern = re.compile(r"^(\d{4}-\d{2}-\d{2})-")
        match = date_pattern.match(filename)

        if match:
            try:
                return datetime.date.fromisoformat(match.group(1))
            except ValueError:
                pass

        return None


# Global service instance
_markdown_service: MarkdownService | None = None


def get_markdown_service(config: Config | None = None) -> MarkdownService:
    """Get the global markdown service instance."""
    global _markdown_service
    if _markdown_service is None:
        style = config.theme.pygments_style if config else "monokai"
        _markdown_service = MarkdownService(pygments_style=style)
    return _markdown_service


def reset_markdown_service() -> None:
    """Reset the global markdown service. Useful for testing or config changes."""
    global _markdown_service
    _markdown_service = None
