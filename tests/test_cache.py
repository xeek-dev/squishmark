"""Tests for cache service."""

import asyncio

import pytest

from squishmark.services.cache import Cache


@pytest.fixture
def cache():
    """Create a cache instance with short TTL for testing."""
    return Cache(ttl_seconds=1)


@pytest.mark.asyncio
async def test_cache_set_get(cache):
    """Test basic cache set and get."""
    await cache.set("key", "value")
    result = await cache.get("key")
    assert result == "value"


@pytest.mark.asyncio
async def test_cache_get_missing(cache):
    """Test getting a missing key."""
    result = await cache.get("nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_cache_delete(cache):
    """Test cache deletion."""
    await cache.set("key", "value")
    deleted = await cache.delete("key")
    assert deleted is True

    result = await cache.get("key")
    assert result is None


@pytest.mark.asyncio
async def test_cache_delete_missing(cache):
    """Test deleting a missing key."""
    deleted = await cache.delete("nonexistent")
    assert deleted is False


@pytest.mark.asyncio
async def test_cache_clear(cache):
    """Test clearing the cache."""
    await cache.set("key1", "value1")
    await cache.set("key2", "value2")

    count = await cache.clear()
    assert count == 2
    assert cache.size == 0


@pytest.mark.asyncio
async def test_cache_expiration(cache):
    """Test that cache entries expire."""
    await cache.set("key", "value", ttl_seconds=0)

    # Small delay to ensure expiration
    await asyncio.sleep(0.1)

    result = await cache.get("key")
    assert result is None


@pytest.mark.asyncio
async def test_cache_size(cache):
    """Test cache size property."""
    assert cache.size == 0

    await cache.set("key1", "value1")
    assert cache.size == 1

    await cache.set("key2", "value2")
    assert cache.size == 2


@pytest.mark.asyncio
async def test_cache_custom_ttl(cache):
    """Test setting custom TTL per entry."""
    await cache.set("short", "value", ttl_seconds=0)
    await cache.set("long", "value", ttl_seconds=3600)

    await asyncio.sleep(0.1)

    assert await cache.get("short") is None
    assert await cache.get("long") == "value"
