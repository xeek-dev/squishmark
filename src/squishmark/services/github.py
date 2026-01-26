"""GitHub content fetching service."""

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from squishmark.config import Settings
from squishmark.services.cache import Cache, get_cache


@dataclass
class GitHubFile:
    """Represents a file fetched from GitHub or local filesystem."""

    path: str
    content: str
    sha: str | None = None


@dataclass
class GitHubBinaryFile:
    """Represents a binary file fetched from GitHub or local filesystem."""

    path: str
    content: bytes
    content_type: str


class GitHubService:
    """Service for fetching content from GitHub or local filesystem."""

    GITHUB_API_BASE = "https://api.github.com"
    GITHUB_RAW_BASE = "https://raw.githubusercontent.com"

    def __init__(self, settings: Settings, cache: Cache | None = None) -> None:
        self.settings = settings
        self.cache = cache or get_cache()
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None:
            headers = {
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "SquishMark/0.1.0",
            }
            if self.settings.github_token:
                headers["Authorization"] = f"Bearer {self.settings.github_token}"
            self._client = httpx.AsyncClient(headers=headers, timeout=30.0)
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _get_local_path(self) -> Path:
        """Get the local content path from file:// URL."""
        url = self.settings.github_content_repo
        if url.startswith("file://"):
            path = url[7:]
            # Handle Windows paths like file:///D:/path
            if len(path) > 2 and path[0] == "/" and path[2] == ":":
                path = path[1:]
            return Path(path)
        raise ValueError(f"Not a file:// URL: {url}")

    async def _fetch_local_file(self, path: str) -> GitHubFile | None:
        """Fetch a file from the local filesystem."""
        try:
            base_path = self._get_local_path()
            file_path = base_path / path

            if not file_path.exists():
                return None

            # Run file read in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            content = await loop.run_in_executor(None, lambda: file_path.read_text(encoding="utf-8"))

            return GitHubFile(path=path, content=content)
        except Exception:
            return None

    async def _fetch_github_file(self, path: str, ref: str = "main") -> GitHubFile | None:
        """Fetch a file from GitHub API."""
        client = await self._get_client()
        repo = self.settings.github_content_repo

        # Use raw content URL for simplicity
        url = f"{self.GITHUB_RAW_BASE}/{repo}/{ref}/{path}"

        try:
            response = await client.get(url)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return GitHubFile(path=path, content=response.text)
        except httpx.HTTPError:
            return None

    async def get_file(self, path: str, ref: str = "main", use_cache: bool = True) -> GitHubFile | None:
        """
        Fetch a file from the content repository.

        Args:
            path: Path to the file within the repository
            ref: Git ref (branch, tag, or commit) - only used for GitHub
            use_cache: Whether to use cached content

        Returns:
            GitHubFile if found, None otherwise
        """
        cache_key = f"file:{path}:{ref}"

        # Check cache first
        if use_cache:
            cached = await self.cache.get(cache_key)
            if cached is not None:
                return cached

        # Fetch from source
        if self.settings.is_local_content:
            result = await self._fetch_local_file(path)
        else:
            result = await self._fetch_github_file(path, ref)

        # Cache the result (even None to avoid repeated lookups)
        if use_cache and result is not None:
            await self.cache.set(cache_key, result)

        return result

    def _get_content_type(self, path: str) -> str:
        """Get content type based on file extension."""
        ext = Path(path).suffix.lower()
        content_types = {
            ".ico": "image/x-icon",
            ".png": "image/png",
            ".svg": "image/svg+xml",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
            ".gif": "image/gif",
            ".css": "text/css",
            ".js": "application/javascript",
        }
        return content_types.get(ext, "application/octet-stream")

    async def _fetch_local_binary_file(self, path: str) -> GitHubBinaryFile | None:
        """Fetch a binary file from the local filesystem."""
        try:
            base_path = self._get_local_path()
            file_path = base_path / path

            if not file_path.exists():
                return None

            loop = asyncio.get_event_loop()
            content = await loop.run_in_executor(None, lambda: file_path.read_bytes())

            return GitHubBinaryFile(
                path=path,
                content=content,
                content_type=self._get_content_type(path),
            )
        except Exception:
            return None

    async def _fetch_github_binary_file(self, path: str, ref: str = "main") -> GitHubBinaryFile | None:
        """Fetch a binary file from GitHub."""
        client = await self._get_client()
        repo = self.settings.github_content_repo

        url = f"{self.GITHUB_RAW_BASE}/{repo}/{ref}/{path}"

        try:
            response = await client.get(url)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return GitHubBinaryFile(
                path=path,
                content=response.content,
                content_type=self._get_content_type(path),
            )
        except httpx.HTTPError:
            return None

    async def get_binary_file(self, path: str, ref: str = "main", use_cache: bool = True) -> GitHubBinaryFile | None:
        """
        Fetch a binary file from the content repository.

        Args:
            path: Path to the file within the repository
            ref: Git ref (branch, tag, or commit) - only used for GitHub
            use_cache: Whether to use cached content

        Returns:
            GitHubBinaryFile if found, None otherwise
        """
        cache_key = f"binary:{path}:{ref}"

        if use_cache:
            cached = await self.cache.get(cache_key)
            if cached is not None:
                return cached

        if self.settings.is_local_content:
            result = await self._fetch_local_binary_file(path)
        else:
            result = await self._fetch_github_binary_file(path, ref)

        if use_cache and result is not None:
            await self.cache.set(cache_key, result)

        return result

    async def _list_local_directory(self, path: str) -> list[str]:
        """List files in a local directory."""
        try:
            base_path = self._get_local_path()
            dir_path = base_path / path

            if not dir_path.exists() or not dir_path.is_dir():
                return []

            loop = asyncio.get_event_loop()

            def _list_files() -> list[str]:
                files = []
                for item in dir_path.iterdir():
                    if item.is_file() and not item.name.startswith("."):
                        files.append(f"{path}/{item.name}")
                return sorted(files)

            return await loop.run_in_executor(None, _list_files)
        except Exception:
            return []

    async def _list_github_directory(self, path: str, ref: str = "main") -> list[str]:
        """List files in a GitHub directory using the API."""
        client = await self._get_client()
        repo = self.settings.github_content_repo

        url = f"{self.GITHUB_API_BASE}/repos/{repo}/contents/{path}"
        params = {"ref": ref}

        try:
            response = await client.get(url, params=params)
            if response.status_code == 404:
                return []
            response.raise_for_status()

            items = response.json()
            if not isinstance(items, list):
                return []

            return sorted([item["path"] for item in items if item["type"] == "file"])
        except httpx.HTTPError:
            return []

    async def list_directory(self, path: str, ref: str = "main", use_cache: bool = True) -> list[str]:
        """
        List files in a directory.

        Args:
            path: Directory path within the repository
            ref: Git ref (branch, tag, or commit) - only used for GitHub
            use_cache: Whether to use cached content

        Returns:
            List of file paths within the directory
        """
        cache_key = f"dir:{path}:{ref}"

        # Check cache first
        if use_cache:
            cached = await self.cache.get(cache_key)
            if cached is not None:
                return cached

        # Fetch from source
        if self.settings.is_local_content:
            result = await self._list_local_directory(path)
        else:
            result = await self._list_github_directory(path, ref)

        # Cache the result
        if use_cache:
            await self.cache.set(cache_key, result)

        return result

    async def get_config(self, use_cache: bool = True) -> dict[str, Any] | None:
        """
        Fetch and parse the config.yml file from the content repository.

        Returns:
            Parsed config dictionary or None if not found
        """
        import yaml

        cache_key = "config"

        if use_cache:
            cached = await self.cache.get(cache_key)
            if cached is not None:
                return cached

        file = await self.get_file("config.yml", use_cache=False)
        if file is None:
            # Try config.yaml as fallback
            file = await self.get_file("config.yaml", use_cache=False)

        if file is None:
            return None

        try:
            config = yaml.safe_load(file.content)
            if use_cache:
                await self.cache.set(cache_key, config)
            return config
        except yaml.YAMLError:
            return None


# Global service instance
_github_service: GitHubService | None = None


def get_github_service() -> GitHubService:
    """Get the global GitHub service instance."""
    global _github_service
    if _github_service is None:
        from squishmark.config import get_settings

        _github_service = GitHubService(get_settings())
    return _github_service


async def shutdown_github_service() -> None:
    """Shutdown the global GitHub service."""
    global _github_service
    if _github_service:
        await _github_service.close()
        _github_service = None
