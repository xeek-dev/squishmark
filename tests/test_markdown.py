"""Tests for markdown processing."""

from datetime import date

import pytest

from squishmark.services.markdown import MarkdownService


@pytest.fixture
def markdown_service():
    """Create a markdown service instance."""
    return MarkdownService()


def test_parse_frontmatter(markdown_service):
    """Test frontmatter parsing."""
    content = """---
title: Test Post
date: 2026-01-25
tags: [python, testing]
---

This is the content.
"""
    frontmatter, body = markdown_service.parse_frontmatter(content)

    assert frontmatter.title == "Test Post"
    assert frontmatter.date == date(2026, 1, 25)
    assert frontmatter.tags == ["python", "testing"]
    assert "This is the content." in body


def test_parse_frontmatter_no_frontmatter(markdown_service):
    """Test parsing content without frontmatter."""
    content = "Just some content without frontmatter."

    frontmatter, body = markdown_service.parse_frontmatter(content)

    assert frontmatter.title == "Untitled"
    assert frontmatter.date is None
    assert frontmatter.tags == []
    assert body == content


def test_render_markdown(markdown_service):
    """Test markdown rendering."""
    content = "# Hello World\n\nThis is **bold** and *italic*."

    html = markdown_service.render_markdown(content)

    assert "<h1>" in html
    assert "Hello World" in html
    assert "<strong>bold</strong>" in html
    assert "<em>italic</em>" in html


def test_render_code_block(markdown_service):
    """Test code block rendering with syntax highlighting."""
    content = """
```python
def hello():
    print("Hello, World!")
```
"""
    html = markdown_service.render_markdown(content)

    assert "highlight" in html
    assert "def" in html


def test_parse_post(markdown_service):
    """Test parsing a full post."""
    content = """---
title: My Post
date: 2026-01-25
tags: [test]
description: A test post
---

Post content here.
"""
    post = markdown_service.parse_post("posts/2026-01-25-my-post.md", content)

    assert post.slug == "my-post"
    assert post.title == "My Post"
    assert post.date == date(2026, 1, 25)
    assert post.tags == ["test"]
    assert post.description == "A test post"
    assert "Post content here." in post.html


def test_extract_date_from_path(markdown_service):
    """Test date extraction from filename."""
    date_result = markdown_service._extract_date_from_path("posts/2026-01-15-hello-world.md")
    assert date_result == date(2026, 1, 15)

    no_date = markdown_service._extract_date_from_path("posts/hello-world.md")
    assert no_date is None


def test_extract_slug(markdown_service):
    """Test slug extraction from path."""
    slug = markdown_service._extract_slug("posts/2026-01-15-hello-world.md")
    assert slug == "hello-world"

    slug_no_date = markdown_service._extract_slug("pages/about.md", strip_date=False)
    assert slug_no_date == "about"
