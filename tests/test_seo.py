"""Tests for SEO routes: sitemap.xml and robots.txt."""

import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from xml.etree.ElementTree import fromstring

import pytest

from squishmark.models.content import Config, Page, Post
from squishmark.routers.seo import _build_robots_txt, _build_sitemap

SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"


def _ns(tag: str) -> str:
    """Prefix a tag with the sitemap namespace."""
    return f"{{{SITEMAP_NS}}}{tag}"


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
def sample_config_no_url() -> Config:
    return Config.from_dict(
        {
            "site": {
                "title": "Test Blog",
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
        ),
        Post(
            slug="post-two",
            title="Post Two",
            date=datetime.date(2026, 2, 10),
            html="<p>Content two</p>",
        ),
    ]


@pytest.fixture
def sample_pages() -> list[Page]:
    return [
        Page(slug="about", title="About", visibility="public"),
        Page(slug="secret", title="Secret", visibility="unlisted"),
        Page(slug="hidden-page", title="Hidden", visibility="hidden"),
    ]


class TestBuildSitemap:
    def test_valid_xml_structure(self, sample_config, sample_posts, sample_pages):
        xml_bytes = _build_sitemap(sample_config, sample_posts, sample_pages)

        assert xml_bytes.startswith(b'<?xml version="1.0" encoding="utf-8"?>')
        root = fromstring(xml_bytes)
        assert root.tag == _ns("urlset")

    def test_homepage_entry(self, sample_config, sample_posts, sample_pages):
        xml_bytes = _build_sitemap(sample_config, sample_posts, sample_pages)
        root = fromstring(xml_bytes)
        urls = root.findall(_ns("url"))

        # First URL should be homepage
        loc = urls[0].find(_ns("loc")).text
        assert loc == "https://example.com/"

    def test_homepage_lastmod_from_newest_post(self, sample_config, sample_posts, sample_pages):
        xml_bytes = _build_sitemap(sample_config, sample_posts, sample_pages)
        root = fromstring(xml_bytes)
        homepage = root.findall(_ns("url"))[0]
        lastmod = homepage.find(_ns("lastmod")).text
        assert lastmod == "2026-02-15"

    def test_post_index_entry(self, sample_config, sample_posts, sample_pages):
        xml_bytes = _build_sitemap(sample_config, sample_posts, sample_pages)
        root = fromstring(xml_bytes)
        urls = root.findall(_ns("url"))
        post_index = [u for u in urls if u.find(_ns("loc")).text == "https://example.com/posts"][0]
        assert post_index.find(_ns("lastmod")).text == "2026-02-15"

    def test_posts_included_with_lastmod(self, sample_config, sample_posts, sample_pages):
        xml_bytes = _build_sitemap(sample_config, sample_posts, sample_pages)
        root = fromstring(xml_bytes)
        urls = root.findall(_ns("url"))

        post_urls = {u.find(_ns("loc")).text: u for u in urls}

        post_one = post_urls["https://example.com/posts/post-one"]
        assert post_one.find(_ns("lastmod")).text == "2026-02-15"

        post_two = post_urls["https://example.com/posts/post-two"]
        assert post_two.find(_ns("lastmod")).text == "2026-02-10"

    def test_public_pages_included(self, sample_config, sample_posts, sample_pages):
        xml_bytes = _build_sitemap(sample_config, sample_posts, sample_pages)
        root = fromstring(xml_bytes)
        locs = [u.find(_ns("loc")).text for u in root.findall(_ns("url"))]
        assert "https://example.com/about" in locs

    def test_unlisted_pages_excluded(self, sample_config, sample_posts, sample_pages):
        xml_bytes = _build_sitemap(sample_config, sample_posts, sample_pages)
        root = fromstring(xml_bytes)
        locs = [u.find(_ns("loc")).text for u in root.findall(_ns("url"))]
        assert "https://example.com/secret" not in locs

    def test_hidden_pages_excluded(self, sample_config, sample_posts, sample_pages):
        xml_bytes = _build_sitemap(sample_config, sample_posts, sample_pages)
        root = fromstring(xml_bytes)
        locs = [u.find(_ns("loc")).text for u in root.findall(_ns("url"))]
        assert "https://example.com/hidden-page" not in locs

    def test_empty_content(self, sample_config):
        xml_bytes = _build_sitemap(sample_config, [], [])
        root = fromstring(xml_bytes)
        urls = root.findall(_ns("url"))
        # Only homepage and post index
        assert len(urls) == 2
        locs = [u.find(_ns("loc")).text for u in urls]
        assert "https://example.com/" in locs
        assert "https://example.com/posts" in locs

    def test_no_site_url_uses_relative_paths(self, sample_config_no_url, sample_posts, sample_pages):
        xml_bytes = _build_sitemap(sample_config_no_url, sample_posts, sample_pages)
        root = fromstring(xml_bytes)
        locs = [u.find(_ns("loc")).text for u in root.findall(_ns("url"))]
        assert "/" in locs
        assert "/posts" in locs
        assert "/posts/post-one" in locs

    def test_post_without_date_has_no_lastmod(self, sample_config):
        post = Post(slug="no-date", title="No Date", html="<p>Hi</p>")
        xml_bytes = _build_sitemap(sample_config, [post], [])
        root = fromstring(xml_bytes)
        urls = root.findall(_ns("url"))
        post_url = [u for u in urls if u.find(_ns("loc")).text == "https://example.com/posts/no-date"][0]
        assert post_url.find(_ns("lastmod")) is None

    def test_no_priority_or_changefreq(self, sample_config, sample_posts, sample_pages):
        """Sitemap should not include priority or changefreq elements."""
        xml_bytes = _build_sitemap(sample_config, sample_posts, sample_pages)
        root = fromstring(xml_bytes)
        for url in root.findall(_ns("url")):
            assert url.find(_ns("priority")) is None
            assert url.find(_ns("changefreq")) is None


class TestBuildRobotsTxt:
    def test_allows_all_crawlers(self, sample_config):
        content = _build_robots_txt(sample_config)
        assert "User-agent: *" in content
        assert "Allow: /" in content

    def test_disallow_admin_paths(self, sample_config):
        content = _build_robots_txt(sample_config)
        assert "Disallow: /admin/*" in content
        assert "Disallow: /auth/*" in content
        assert "Disallow: /health" in content
        assert "Disallow: /webhooks/*" in content

    def test_sitemap_directive_with_url(self, sample_config):
        content = _build_robots_txt(sample_config)
        assert "Sitemap: https://example.com/sitemap.xml" in content

    def test_no_sitemap_without_url(self, sample_config_no_url):
        content = _build_robots_txt(sample_config_no_url)
        assert "Sitemap" not in content

    def test_no_static_disallow(self, sample_config):
        """Static files should not be blocked."""
        content = _build_robots_txt(sample_config)
        assert "/static" not in content


class TestSitemapEndpoint:
    @pytest.mark.asyncio
    async def test_returns_xml_content_type(self):
        mock_github = AsyncMock()
        mock_github.get_config.return_value = {"site": {"title": "Test"}}
        mock_github.list_directory.return_value = []

        with (
            patch("squishmark.routers.seo.get_github_service", return_value=mock_github),
            patch("squishmark.routers.seo.get_cache") as mock_cache_fn,
        ):
            mock_cache = AsyncMock()
            mock_cache.get.return_value = None
            mock_cache_fn.return_value = mock_cache

            from squishmark.routers.seo import sitemap_xml

            response = await sitemap_xml()

        assert "application/xml" in response.media_type

    @pytest.mark.asyncio
    async def test_cached_response_returned(self):
        cached_xml = b'<?xml version="1.0"?><urlset>cached</urlset>'

        with patch("squishmark.routers.seo.get_cache") as mock_cache_fn:
            mock_cache = AsyncMock()
            mock_cache.get.return_value = cached_xml
            mock_cache_fn.return_value = mock_cache

            from squishmark.routers.seo import sitemap_xml

            response = await sitemap_xml()

        assert response.body == cached_xml

    @pytest.mark.asyncio
    async def test_drafts_excluded(self):
        mock_github = AsyncMock()
        mock_github.get_config.return_value = {
            "site": {"title": "Test", "url": "https://example.com"},
        }
        mock_github.list_directory.side_effect = [
            # posts directory
            ["posts/2026-01-01-published.md", "posts/2026-01-02-draft.md"],
            # pages directory
            [],
        ]
        mock_github.get_file.side_effect = [
            MagicMock(content="---\ntitle: Published\ndate: 2026-01-01\n---\nContent."),
            MagicMock(content="---\ntitle: Draft\ndate: 2026-01-02\ndraft: true\n---\nDraft."),
        ]

        with (
            patch("squishmark.routers.seo.get_github_service", return_value=mock_github),
            patch("squishmark.routers.seo.get_cache") as mock_cache_fn,
        ):
            mock_cache = AsyncMock()
            mock_cache.get.return_value = None
            mock_cache_fn.return_value = mock_cache

            from squishmark.routers.seo import sitemap_xml

            response = await sitemap_xml()

        root = fromstring(response.body)
        locs = [u.find(_ns("loc")).text for u in root.findall(_ns("url"))]
        assert "https://example.com/posts/published" in locs
        assert "https://example.com/posts/draft" not in locs


class TestRobotsEndpoint:
    @pytest.mark.asyncio
    async def test_returns_text_content_type(self):
        mock_github = AsyncMock()
        mock_github.get_config.return_value = {"site": {"title": "Test"}}

        with (
            patch("squishmark.routers.seo.get_github_service", return_value=mock_github),
            patch("squishmark.routers.seo.get_cache") as mock_cache_fn,
        ):
            mock_cache = AsyncMock()
            mock_cache.get.return_value = None
            mock_cache_fn.return_value = mock_cache

            from squishmark.routers.seo import robots_txt

            response = await robots_txt()

        assert "text/plain" in response.media_type

    @pytest.mark.asyncio
    async def test_cached_response_returned(self):
        cached_txt = "User-agent: *\nAllow: /\n"

        with patch("squishmark.routers.seo.get_cache") as mock_cache_fn:
            mock_cache = AsyncMock()
            mock_cache.get.return_value = cached_txt
            mock_cache_fn.return_value = mock_cache

            from squishmark.routers.seo import robots_txt

            response = await robots_txt()

        assert response.body.decode() == cached_txt
