"""In-memory cache with TTL support."""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any


@dataclass
class CacheEntry:
    """A single cache entry with expiration time."""

    value: Any
    expires_at: datetime


@dataclass
class Cache:
    """Simple in-memory cache with TTL support."""

    ttl_seconds: int = 300
    _store: dict[str, CacheEntry] = field(default_factory=dict)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def get(self, key: str) -> Any | None:
        """Get a value from the cache if it exists and hasn't expired."""
        async with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if datetime.now() > entry.expires_at:
                del self._store[key]
                return None
            return entry.value

    async def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        """Set a value in the cache with optional custom TTL."""
        ttl = ttl_seconds if ttl_seconds is not None else self.ttl_seconds
        expires_at = datetime.now() + timedelta(seconds=ttl)
        async with self._lock:
            self._store[key] = CacheEntry(value=value, expires_at=expires_at)

    async def delete(self, key: str) -> bool:
        """Delete a key from the cache. Returns True if key existed."""
        async with self._lock:
            if key in self._store:
                del self._store[key]
                return True
            return False

    async def clear(self) -> int:
        """Clear all entries from the cache. Returns number of entries cleared."""
        async with self._lock:
            count = len(self._store)
            self._store.clear()
            return count

    async def cleanup_expired(self) -> int:
        """Remove all expired entries. Returns number of entries removed."""
        async with self._lock:
            now = datetime.now()
            expired_keys = [k for k, v in self._store.items() if now > v.expires_at]
            for key in expired_keys:
                del self._store[key]
            return len(expired_keys)

    @property
    def size(self) -> int:
        """Return the current number of entries in the cache."""
        return len(self._store)


# Global cache instance
_cache: Cache | None = None


def get_cache() -> Cache:
    """Get the global cache instance."""
    global _cache
    if _cache is None:
        from squishmark.config import get_settings

        settings = get_settings()
        ttl = 0 if settings.debug else settings.cache_ttl_seconds
        _cache = Cache(ttl_seconds=ttl)
    return _cache


def reset_cache() -> None:
    """Reset the global cache instance. Useful for testing."""
    global _cache
    _cache = None
