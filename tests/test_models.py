"""Tests for Pydantic models."""

from squishmark.models.content import Post, ThemeConfig


def test_themeconfig_allows_extra_fields():
    """Extra fields in theme config should be accessible as attributes."""
    config = ThemeConfig(name="test", custom_option="value")
    assert config.custom_option == "value"


class TestReadingTime:
    """Tests for Post.reading_time property."""

    def test_short_post_minimum_one_minute(self):
        """A very short post should show 1 min read."""
        post = Post(slug="short", title="Short", html="<p>Hello world.</p>")
        assert post.reading_time == "1 min read"

    def test_empty_content_returns_empty_string(self):
        """Empty content should return empty string."""
        post = Post(slug="empty", title="Empty", html="", content="")
        assert post.reading_time == ""

    def test_whitespace_only_returns_empty_string(self):
        """Whitespace-only content should return empty string."""
        post = Post(slug="ws", title="WS", html="   \n  ", content="")
        assert post.reading_time == ""

    def test_strips_html_tags(self):
        """HTML tags should not count toward word count."""
        # 10 words of actual text wrapped in tags
        html = "<div><p><strong>one two three four five six seven eight nine ten</strong></p></div>"
        post = Post(slug="html", title="HTML", html=html)
        assert post.reading_time == "1 min read"

    def test_longer_post_calculates_correctly(self):
        """A post with ~476 words should be ~2 min read (476/238 = 2.0)."""
        words = " ".join(["word"] * 476)
        post = Post(slug="long", title="Long", html=f"<p>{words}</p>")
        assert post.reading_time == "2 min read"

    def test_rounding_behavior(self):
        """Reading time should round to nearest minute."""
        # 357 words / 238 = 1.5 -> rounds to 2
        words = " ".join(["word"] * 357)
        post = Post(slug="round", title="Round", html=f"<p>{words}</p>")
        assert post.reading_time == "2 min read"

    def test_falls_back_to_content_when_no_html(self):
        """When html is empty, should use raw content for word count."""
        content = " ".join(["word"] * 50)
        post = Post(slug="raw", title="Raw", html="", content=content)
        assert post.reading_time == "1 min read"

    def test_large_post(self):
        """A post with ~1190 words should be ~5 min read."""
        words = " ".join(["word"] * 1190)
        post = Post(slug="large", title="Large", html=f"<p>{words}</p>")
        assert post.reading_time == "5 min read"
