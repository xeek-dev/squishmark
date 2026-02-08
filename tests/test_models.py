"""Tests for Pydantic models."""

from squishmark.models.content import ThemeConfig


def test_themeconfig_allows_extra_fields():
    """Extra fields in theme config should be accessible as attributes."""
    config = ThemeConfig(name="test", custom_option="value")
    assert config.custom_option == "value"
