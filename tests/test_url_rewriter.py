"""Tests for URL rewriting in markdown content."""

from squishmark.services.url_rewriter import (
    ImageSrcCollector,
    _is_child_of_static,
    rewrite_image_urls,
)


class TestImageSrcCollector:
    """Tests for the ImageSrcCollector HTML parser."""

    def test_collects_img_src(self):
        """Test that img src attributes are collected."""
        collector = ImageSrcCollector()
        collector.feed('<img src="image.png" alt="test">')
        assert collector.sources == ["image.png"]

    def test_collects_multiple_images(self):
        """Test collecting multiple image sources."""
        collector = ImageSrcCollector()
        collector.feed('<img src="a.png"><p>text</p><img src="b.jpg">')
        assert collector.sources == ["a.png", "b.jpg"]

    def test_ignores_non_img_tags(self):
        """Test that non-img tags are ignored."""
        collector = ImageSrcCollector()
        collector.feed('<a href="link.html">text</a><script src="app.js"></script>')
        assert collector.sources == []

    def test_handles_empty_src(self):
        """Test that empty src is ignored."""
        collector = ImageSrcCollector()
        collector.feed('<img src="" alt="empty">')
        assert collector.sources == []


class TestIsChildOfStatic:
    """Tests for the _is_child_of_static security check."""

    def test_valid_static_path(self):
        """Test valid path under static/."""
        assert _is_child_of_static("static/images/pic.png") is True

    def test_valid_nested_static_path(self):
        """Test valid nested path under static/."""
        assert _is_child_of_static("static/ai/2026/pic.png") is True

    def test_rejects_traversal_outside_static(self):
        """Test that traversal outside static/ is rejected."""
        assert _is_child_of_static("../etc/passwd") is False
        assert _is_child_of_static("posts/../../etc/passwd") is False

    def test_rejects_traversal_through_static(self):
        """Test that traversal through static/ then out is rejected."""
        assert _is_child_of_static("static/../../../etc/passwd") is False

    def test_rejects_url_encoded_traversal(self):
        """Test that URL-encoded traversal is detected and rejected."""
        # %2e%2e is URL-encoded ..
        assert _is_child_of_static("static/%2e%2e/%2e%2e/etc/passwd") is False

    def test_rejects_static_prefix_only(self):
        """Test that 'static' alone (without a file) is rejected."""
        assert _is_child_of_static("static") is False
        assert _is_child_of_static("static/") is False

    def test_rejects_staticfake_directory(self):
        """Test that directories starting with 'static' but not 'static/' are rejected."""
        assert _is_child_of_static("staticfake/img.png") is False


class TestRewriteImageUrls:
    """Tests for the rewrite_image_urls function."""

    def test_rewrite_relative_to_static(self):
        """Test basic rewriting of relative paths to static/."""
        html = '<p><img src="../static/images/pic.png" alt="test"></p>'
        result = rewrite_image_urls(html, "posts/2026-01-15-hello.md")
        assert 'src="/static/user/images/pic.png"' in result

    def test_nested_content_folders(self):
        """Test rewriting with deeply nested content folders."""
        html = '<img src="../../../static/charts/q1.png">'
        result = rewrite_image_urls(html, "pages/projects/2026/roadmap.md")
        assert 'src="/static/user/charts/q1.png"' in result

    def test_preserves_nested_static_structure(self):
        """Test that nested paths under static/ are preserved."""
        html = '<img src="../static/ai/2026/generated/pic.png">'
        result = rewrite_image_urls(html, "posts/hello.md")
        assert 'src="/static/user/ai/2026/generated/pic.png"' in result

    def test_preserves_absolute_http_urls(self):
        """Test that http:// URLs are unchanged."""
        html = '<img src="http://example.com/img.png">'
        result = rewrite_image_urls(html, "posts/hello.md")
        assert 'src="http://example.com/img.png"' in result

    def test_preserves_absolute_https_urls(self):
        """Test that https:// URLs are unchanged."""
        html = '<img src="https://example.com/img.png">'
        result = rewrite_image_urls(html, "posts/hello.md")
        assert 'src="https://example.com/img.png"' in result

    def test_preserves_protocol_relative_urls(self):
        """Test that // URLs are unchanged."""
        html = '<img src="//cdn.example.com/img.png">'
        result = rewrite_image_urls(html, "posts/hello.md")
        assert 'src="//cdn.example.com/img.png"' in result

    def test_preserves_root_relative_urls(self):
        """Test that /path URLs are unchanged."""
        html = '<img src="/static/user/img.png">'
        result = rewrite_image_urls(html, "posts/hello.md")
        assert 'src="/static/user/img.png"' in result

    def test_ignores_non_static_relative_paths(self):
        """Test that relative paths not to static/ are unchanged."""
        html = '<img src="./local-image.png">'
        result = rewrite_image_urls(html, "posts/hello.md")
        assert 'src="./local-image.png"' in result

    def test_handles_single_quotes(self):
        """Test that single-quoted src attributes are handled."""
        html = "<img src='../static/img.png'>"
        result = rewrite_image_urls(html, "posts/hello.md")
        assert "src='/static/user/img.png'" in result

    def test_handles_multiple_images(self):
        """Test rewriting multiple images in one document."""
        html = '<img src="../static/a.png"><img src="../static/b.png">'
        result = rewrite_image_urls(html, "posts/hello.md")
        assert 'src="/static/user/a.png"' in result
        assert 'src="/static/user/b.png"' in result

    def test_blocks_traversal_attack(self):
        """Test that path traversal attacks are blocked."""
        html = '<img src="../../../etc/passwd">'
        result = rewrite_image_urls(html, "posts/hello.md")
        # The original src should be unchanged (not rewritten)
        assert 'src="../../../etc/passwd"' in result

    def test_blocks_traversal_through_static(self):
        """Test that traversal through static/ then out is blocked."""
        html = '<img src="../static/../../../etc/passwd">'
        result = rewrite_image_urls(html, "posts/hello.md")
        # The original src should be unchanged (not rewritten)
        assert 'src="../static/../../../etc/passwd"' in result

    def test_blocks_url_encoded_traversal(self):
        """Test that URL-encoded traversal attacks are blocked."""
        html = '<img src="../static/%2e%2e/%2e%2e/etc/passwd">'
        result = rewrite_image_urls(html, "posts/hello.md")
        # The original src should be unchanged (not rewritten)
        assert 'src="../static/%2e%2e/%2e%2e/etc/passwd"' in result

    def test_returns_unchanged_when_no_images(self):
        """Test fast path when HTML has no images."""
        html = "<p>Just some text</p>"
        result = rewrite_image_urls(html, "posts/hello.md")
        assert result == html

    def test_pages_directory(self):
        """Test rewriting for pages (not posts)."""
        html = '<img src="../static/images/me.jpg">'
        result = rewrite_image_urls(html, "pages/about.md")
        assert 'src="/static/user/images/me.jpg"' in result
