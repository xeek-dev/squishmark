"""Favicon detection for content repositories."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from squishmark.services.github import GitHubService


# Favicon candidates in order of preference
FAVICON_CANDIDATES = [
    ("static/favicon.ico", "image/x-icon"),
    ("static/favicon.png", "image/png"),
    ("static/favicon.svg", "image/svg+xml"),
]


class FaviconDetector:
    """Detects and caches favicon from content repository."""

    def __init__(self, github_service: "GitHubService") -> None:
        self.github_service = github_service
        self._favicon_url: str | None = None
        self._favicon_checked: bool = False

    async def detect(self) -> str | None:
        """
        Detect the favicon file in the content repository.

        Returns:
            URL path to the favicon (e.g., "/static/user/favicon.png") or None
        """
        if self._favicon_checked:
            return self._favicon_url

        self._favicon_checked = True

        for path, _content_type in FAVICON_CANDIDATES:
            file = await self.github_service.get_binary_file(path)
            if file:
                # Convert "static/favicon.png" to "/static/user/favicon.png"
                filename = path.replace("static/", "")
                self._favicon_url = f"/static/user/{filename}"
                return self._favicon_url

        return None

    def clear_cache(self) -> None:
        """Clear the cached favicon URL."""
        self._favicon_url = None
        self._favicon_checked = False
