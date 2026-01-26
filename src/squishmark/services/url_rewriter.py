"""URL rewriting for relative image paths in markdown content."""

import posixpath
from html.parser import HTMLParser
from pathlib import PurePosixPath
from urllib.parse import unquote


class ImageSrcCollector(HTMLParser):
    """Collects src attribute values from img tags in HTML."""

    def __init__(self) -> None:
        super().__init__()
        self.sources: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "img":
            for name, value in attrs:
                if name == "src" and value:
                    self.sources.append(value)


def _is_child_of_static(resolved: str) -> bool:
    """Check if resolved path is actually a child of static/ directory."""
    # URL-decode first to catch encoded traversal attempts (%2e%2e -> ..)
    decoded = unquote(resolved)
    # Normalize the decoded path to resolve any .. components
    normalized = posixpath.normpath(decoded)

    # Use path parts to verify it's under static/
    parts = PurePosixPath(normalized).parts

    # Must have 'static' as first component and at least one more (the file)
    if len(parts) < 2 or parts[0] != "static":
        return False

    # Belt and suspenders: reject if any part is '..'
    if ".." in parts:
        return False

    return True


def rewrite_image_urls(html: str, file_path: str) -> str:
    """
    Rewrite relative image URLs to absolute /static/user/ paths.

    Args:
        html: Rendered HTML content
        file_path: Path of the source file (e.g., "posts/2026-01-15-hello.md")

    Returns:
        HTML with rewritten image URLs
    """
    file_dir = posixpath.dirname(file_path)

    collector = ImageSrcCollector()
    collector.feed(html)

    if not collector.sources:
        return html  # Fast path: no images

    replacements: dict[str, str] = {}
    for src in collector.sources:
        # Skip absolute URLs
        if src.startswith(("http://", "https://", "//", "/")):
            continue

        # Resolve relative path
        resolved = posixpath.normpath(posixpath.join(file_dir, src))

        # Security check: verify path is under static/
        if _is_child_of_static(resolved):
            rest = resolved[7:]  # Remove "static/" prefix
            replacements[src] = f"/static/user/{rest}"

    if not replacements:
        return html

    # Apply replacements (both quote styles)
    for old, new in replacements.items():
        html = html.replace(f'src="{old}"', f'src="{new}"')
        html = html.replace(f"src='{old}'", f"src='{new}'")

    return html
