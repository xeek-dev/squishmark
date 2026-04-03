"""SEO routes: sitemap.xml and robots.txt."""

from xml.etree.ElementTree import Element, SubElement, tostring

from fastapi import APIRouter
from fastapi.responses import Response

from squishmark.models.content import Config, Page, Post
from squishmark.services.cache import get_cache
from squishmark.services.content import get_all_pages, get_all_posts
from squishmark.services.github import get_github_service
from squishmark.services.markdown import get_markdown_service

router = APIRouter(tags=["seo"])

SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
SITEMAP_CACHE_KEY = "seo:sitemap"
ROBOTS_CACHE_KEY = "seo:robots"


def _build_sitemap(config: Config, posts: list[Post], pages: list[Page]) -> bytes:
    """Build a sitemap.xml from config, posts, and pages."""
    site_url = config.site.url.rstrip("/") if config.site.url else ""

    urlset = Element("urlset", xmlns=SITEMAP_NS)

    # Homepage
    url_el = SubElement(urlset, "url")
    SubElement(url_el, "loc").text = f"{site_url}/"
    if posts and posts[0].date:
        SubElement(url_el, "lastmod").text = posts[0].date.isoformat()

    # Post index
    url_el = SubElement(urlset, "url")
    SubElement(url_el, "loc").text = f"{site_url}/posts"

    # Individual posts
    for post in posts:
        url_el = SubElement(urlset, "url")
        SubElement(url_el, "loc").text = f"{site_url}{post.url}"
        if post.date:
            SubElement(url_el, "lastmod").text = post.date.isoformat()

    # Public pages only (not unlisted or hidden)
    for page in pages:
        if page.visibility != "public":
            continue
        url_el = SubElement(urlset, "url")
        SubElement(url_el, "loc").text = f"{site_url}{page.url}"

    return b'<?xml version="1.0" encoding="utf-8"?>\n' + tostring(urlset, encoding="unicode").encode("utf-8")


def _build_robots_txt(config: Config) -> str:
    """Build robots.txt content."""
    site_url = config.site.url.rstrip("/") if config.site.url else ""

    lines = [
        "User-agent: *",
        "Allow: /",
        "",
        "Disallow: /admin/*",
        "Disallow: /auth/*",
        "Disallow: /health",
        "Disallow: /webhooks/*",
    ]

    if site_url:
        lines.append("")
        lines.append(f"Sitemap: {site_url}/sitemap.xml")

    return "\n".join(lines) + "\n"


@router.get("/sitemap.xml")
async def sitemap_xml() -> Response:
    """Serve the XML sitemap."""
    cache = get_cache()

    cached = await cache.get(SITEMAP_CACHE_KEY)
    if cached is not None:
        return Response(content=cached, media_type="application/xml; charset=utf-8")

    github_service = get_github_service()
    config_data = await github_service.get_config()
    config = Config.from_dict(config_data)
    markdown_service = get_markdown_service(config)

    posts = await get_all_posts(github_service, markdown_service)
    pages = await get_all_pages(github_service, markdown_service)

    xml_bytes = _build_sitemap(config, posts, pages)
    await cache.set(SITEMAP_CACHE_KEY, xml_bytes)
    return Response(content=xml_bytes, media_type="application/xml; charset=utf-8")


@router.get("/robots.txt")
async def robots_txt() -> Response:
    """Serve robots.txt."""
    cache = get_cache()

    cached = await cache.get(ROBOTS_CACHE_KEY)
    if cached is not None:
        return Response(content=cached, media_type="text/plain; charset=utf-8")

    github_service = get_github_service()
    config_data = await github_service.get_config()
    config = Config.from_dict(config_data)

    content = _build_robots_txt(config)
    await cache.set(ROBOTS_CACHE_KEY, content)
    return Response(content=content, media_type="text/plain; charset=utf-8")
