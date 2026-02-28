"""Tests for Atom feed route."""

import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from xml.etree.ElementTree import fromstring

import pytest

from squishmark.models.content import Config, Post
from squishmark.routers.feed import _build_atom_feed, _rfc3339

ATOM_NS = "http://www.w3.org/2005/Atom"


def _ns(tag: str) -> str:
    """Prefix a tag with the Atom namespace."""
    return f"{{{ATOM_NS}}}{tag}"


@pytest.fixture
def sample_config() -> Config:
    return Config.from_dict(
        {
            "site": {
                "title": "Test Blog",
                "description": "A test blog",
                "author": "Test Author",
                "url": "https://example.com",
            },
        }
    )


@pytest.fixture
def sample_posts() -> list[Post]:
    return [
        Post(
            slug="post-one",
            title="Post One",
            date=datetime.date(2026, 2, 15),
            html="<p>Content one</p>",
            description="First post",
        ),
        Post(
            slug="post-two",
            title="Post Two",
            date=datetime.date(2026, 2, 10),
            html="<p>Content two</p>",
        ),
    ]


class TestRfc3339:
    def test_formats_date_as_rfc3339(self):
        result = _rfc3339(datetime.date(2026, 1, 15))
        assert result == "2026-01-15T00:00:00+00:00"


class TestBuildAtomFeed:
    def test_valid_atom_structure(self, sample_config, sample_posts):
        xml_bytes = _build_atom_feed(sample_config, sample_posts)

        assert xml_bytes.startswith(b'<?xml version="1.0" encoding="utf-8"?>')
        root = fromstring(xml_bytes)
        assert root.tag == _ns("feed")
        assert root.find(_ns("title")).text == "Test Blog"
        assert root.find(_ns("subtitle")).text == "A test blog"
        assert root.find(_ns("id")).text == "https://example.com"

    def test_entries_present(self, sample_config, sample_posts):
        xml_bytes = _build_atom_feed(sample_config, sample_posts)
        root = fromstring(xml_bytes)
        entries = root.findall(_ns("entry"))
        assert len(entries) == 2

    def test_entry_has_required_fields(self, sample_config, sample_posts):
        xml_bytes = _build_atom_feed(sample_config, sample_posts)
        root = fromstring(xml_bytes)
        entry = root.findall(_ns("entry"))[0]

        assert entry.find(_ns("title")).text == "Post One"
        assert entry.find(_ns("id")).text == "https://example.com/posts/post-one"
        assert entry.find(_ns("updated")).text is not None
        assert entry.find(_ns("published")).text is not None
        assert entry.find(_ns("summary")).text == "First post"

    def test_html_content_in_entry(self, sample_config, sample_posts):
        xml_bytes = _build_atom_feed(sample_config, sample_posts)
        root = fromstring(xml_bytes)
        entry = root.findall(_ns("entry"))[0]

        content_el = entry.find(_ns("content"))
        assert content_el.attrib["type"] == "html"
        assert "<p>Content one</p>" in content_el.text

    def test_author_element(self, sample_config, sample_posts):
        xml_bytes = _build_atom_feed(sample_config, sample_posts)
        root = fromstring(xml_bytes)
        author = root.find(_ns("author"))
        assert author.find(_ns("name")).text == "Test Author"

    def test_self_link(self, sample_config, sample_posts):
        xml_bytes = _build_atom_feed(sample_config, sample_posts)
        root = fromstring(xml_bytes)
        links = root.findall(_ns("link"))
        self_link = [link for link in links if link.attrib.get("rel") == "self"][0]
        assert self_link.attrib["href"] == "https://example.com/feed.xml"
        assert self_link.attrib["type"] == "application/atom+xml"

    def test_empty_posts(self, sample_config):
        xml_bytes = _build_atom_feed(sample_config, [])
        root = fromstring(xml_bytes)
        entries = root.findall(_ns("entry"))
        assert len(entries) == 0
        # Should still have an updated element (falls back to now)
        assert root.find(_ns("updated")).text is not None

    def test_entry_without_description_has_no_summary(self, sample_config):
        post = Post(slug="no-desc", title="No Desc", html="<p>Hi</p>")
        xml_bytes = _build_atom_feed(sample_config, [post])
        root = fromstring(xml_bytes)
        entry = root.findall(_ns("entry"))[0]
        assert entry.find(_ns("summary")) is None

    def test_entry_without_date_has_no_timestamps(self, sample_config):
        post = Post(slug="no-date", title="No Date", html="<p>Hi</p>")
        xml_bytes = _build_atom_feed(sample_config, [post])
        root = fromstring(xml_bytes)
        entry = root.findall(_ns("entry"))[0]
        assert entry.find(_ns("updated")) is None
        assert entry.find(_ns("published")) is None


class TestAtomFeedEndpoint:
    @pytest.mark.asyncio
    async def test_draft_posts_excluded(self):
        """Draft posts should not appear in the feed."""
        mock_github = AsyncMock()
        mock_github.get_config.return_value = {
            "site": {"title": "Test", "url": "https://example.com"},
        }
        mock_github.list_directory.return_value = [
            "posts/2026-01-01-published.md",
            "posts/2026-01-02-draft.md",
        ]
        mock_github.get_file.side_effect = [
            MagicMock(content="---\ntitle: Published\ndate: 2026-01-01\n---\nPublished content here."),
            MagicMock(content="---\ntitle: Draft\ndate: 2026-01-02\ndraft: true\n---\nDraft content here."),
        ]

        with (
            patch("squishmark.routers.feed.get_github_service", return_value=mock_github),
            patch("squishmark.routers.feed.get_cache") as mock_cache_fn,
        ):
            mock_cache = AsyncMock()
            mock_cache.get.return_value = None
            mock_cache_fn.return_value = mock_cache

            from squishmark.routers.feed import atom_feed

            response = await atom_feed()

        root = fromstring(response.body)
        entries = root.findall(_ns("entry"))
        assert len(entries) == 1
        assert entries[0].find(_ns("title")).text == "Published"

    @pytest.mark.asyncio
    async def test_limits_to_20_posts(self):
        """Feed should include at most 20 posts."""
        mock_github = AsyncMock()
        mock_github.get_config.return_value = {
            "site": {"title": "Test", "url": "https://example.com"},
        }
        # Create 25 post files
        mock_github.list_directory.return_value = [f"posts/2026-01-{i:02d}-post-{i}.md" for i in range(1, 26)]
        mock_github.get_file.side_effect = [
            MagicMock(content=f"---\ntitle: Post {i}\ndate: 2026-01-{i:02d}\n---\nContent {i}") for i in range(1, 26)
        ]

        with (
            patch("squishmark.routers.feed.get_github_service", return_value=mock_github),
            patch("squishmark.routers.feed.get_cache") as mock_cache_fn,
        ):
            mock_cache = AsyncMock()
            mock_cache.get.return_value = None
            mock_cache_fn.return_value = mock_cache

            from squishmark.routers.feed import atom_feed

            response = await atom_feed()

        root = fromstring(response.body)
        entries = root.findall(_ns("entry"))
        assert len(entries) == 20

    @pytest.mark.asyncio
    async def test_returns_atom_content_type(self):
        """Response should have application/atom+xml content type."""
        mock_github = AsyncMock()
        mock_github.get_config.return_value = {"site": {"title": "Test"}}
        mock_github.list_directory.return_value = []

        with (
            patch("squishmark.routers.feed.get_github_service", return_value=mock_github),
            patch("squishmark.routers.feed.get_cache") as mock_cache_fn,
        ):
            mock_cache = AsyncMock()
            mock_cache.get.return_value = None
            mock_cache_fn.return_value = mock_cache

            from squishmark.routers.feed import atom_feed

            response = await atom_feed()

        assert "application/atom+xml" in response.media_type

    @pytest.mark.asyncio
    async def test_cached_response_returned(self):
        """Cached XML should be returned without rebuilding."""
        cached_xml = b'<?xml version="1.0"?><feed>cached</feed>'

        with patch("squishmark.routers.feed.get_cache") as mock_cache_fn:
            mock_cache = AsyncMock()
            mock_cache.get.return_value = cached_xml
            mock_cache_fn.return_value = mock_cache

            from squishmark.routers.feed import atom_feed

            response = await atom_feed()

        assert response.body == cached_xml
