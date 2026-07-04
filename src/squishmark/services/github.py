"""GitHub content fetching service."""

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from squishmark.config import Settings, parse_file_url
from squishmark.services.cache import Cache

logger = logging.getLogger(__name__)


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

    def __init__(self, settings: Settings, cache: Cache) -> None:
        self.settings = settings
        self.cache = cache
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
        return parse_file_url(self.settings.github_content_repo)

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
            logger.warning("Failed to read local file %r", path, exc_info=True)
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
        except httpx.HTTPError as exc:
            logger.warning("Failed to fetch %s from GitHub: %s", url, exc)
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

        # Cache only successful results; misses stay uncached so they can retry.
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
            logger.warning("Failed to read local binary file %r", path, exc_info=True)
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
        except httpx.HTTPError as exc:
            logger.warning("Failed to fetch binary %s from GitHub: %s", url, exc)
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

    async def _list_local_directory(self, path: str, recursive: bool = False) -> list[str]:
        """List files in a local directory."""
        try:
            base_path = self._get_local_path()
            dir_path = base_path / path

            if not dir_path.exists() or not dir_path.is_dir():
                return []

            loop = asyncio.get_event_loop()

            def _list_files() -> list[str]:
                files = []
                items = dir_path.rglob("*") if recursive else dir_path.iterdir()
                for item in items:
                    if not item.is_file():
                        continue
                    rel = item.relative_to(base_path)
                    if any(part.startswith(".") for part in rel.parts):
                        continue
                    files.append(str(rel))
                return sorted(files)

            return await loop.run_in_executor(None, _list_files)
        except Exception:
            logger.warning("Failed to list local directory %r", path, exc_info=True)
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
        except httpx.HTTPError as exc:
            logger.warning("Failed to list GitHub directory %s: %s", url, exc)
            return []

    async def _list_github_tree(self, path: str, ref: str = "main") -> list[str]:
        """List files under a directory recursively using the git trees API."""
        client = await self._get_client()
        repo = self.settings.github_content_repo

        url = f"{self.GITHUB_API_BASE}/repos/{repo}/git/trees/{ref}"
        params = {"recursive": "1"}

        try:
            response = await client.get(url, params=params)
            if response.status_code == 404:
                return []
            response.raise_for_status()

            data = response.json()
            if data.get("truncated"):
                logger.warning("Git tree for %s is truncated; some files may be missing", repo)

            prefix = f"{path}/"
            return sorted(
                item["path"]
                for item in data.get("tree", [])
                if item.get("type") == "blob" and item.get("path", "").startswith(prefix)
            )
        except httpx.HTTPError as exc:
            logger.warning("Failed to list GitHub tree %s: %s", url, exc)
            return []

    async def list_directory(
        self, path: str, ref: str = "main", use_cache: bool = True, recursive: bool = False
    ) -> list[str]:
        """
        List files in a directory.

        Args:
            path: Directory path within the repository
            ref: Git ref (branch, tag, or commit) - only used for GitHub
            use_cache: Whether to use cached content
            recursive: Whether to include files in subdirectories

        Returns:
            List of file paths within the directory
        """
        cache_key = f"dir:{path}:{ref}:{int(recursive)}"

        # Check cache first
        if use_cache:
            cached = await self.cache.get(cache_key)
            if cached is not None:
                return cached

        # Fetch from source
        if self.settings.is_local_content:
            result = await self._list_local_directory(path, recursive=recursive)
        elif recursive:
            result = await self._list_github_tree(path, ref)
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
        except yaml.YAMLError as exc:
            logger.warning("Failed to parse config YAML: %s", exc)
            return None
