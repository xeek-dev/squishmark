"""Tests for configuration module."""

import pytest

from squishmark.config import Settings


def test_settings_defaults():
    """Test that settings have sensible defaults."""
    settings = Settings(
        _env_file=None,  # Don't load .env file
    )
    assert settings.cache_ttl_seconds == 300
    assert settings.debug is False
    assert settings.admin_users_list == []


def test_admin_users_list():
    """Test parsing of admin users list."""
    settings = Settings(
        admin_users="user1, user2, user3",
        _env_file=None,
    )
    assert settings.admin_users_list == ["user1", "user2", "user3"]


def test_admin_users_list_empty():
    """Test empty admin users list."""
    settings = Settings(
        admin_users="",
        _env_file=None,
    )
    assert settings.admin_users_list == []


def test_is_local_content():
    """Test local content detection."""
    settings = Settings(
        github_content_repo="file:///path/to/content",
        _env_file=None,
    )
    assert settings.is_local_content is True

    settings = Settings(
        github_content_repo="xeek-dev/content",
        _env_file=None,
    )
    assert settings.is_local_content is False
