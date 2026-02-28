"""Atom feed route."""

import datetime
from xml.etree.ElementTree import Element, SubElement, tostring

from fastapi import APIRouter
from fastapi.responses import Response

from squishmark.models.content import Config, Post
from squishmark.services.cache import get_cache
from squishmark.services.github import get_github_service
from squishmark.services.markdown import get_markdown_service

router = APIRouter(tags=["feed"])

ATOM_NS = "http://www.w3.org/2005/Atom"


def _rfc3339(d: datetime.date) -> str:
    """Format a date as RFC 3339 (required by Atom)."""
    return datetime.datetime.combine(d, datetime.time(), tzinfo=datetime.timezone.utc).isoformat()


def _build_atom_feed(config: Config, posts: list[Post]) -> bytes:
    """Build an Atom 1.0 XML feed from config and posts."""
    site = config.site
    site_url = site.url.rstrip("/") if site.url else ""

    feed = Element("feed", xmlns=ATOM_NS)

    SubElement(feed, "title").text = site.title
    if site.description:
        SubElement(feed, "subtitle").text = site.description
    SubElement(feed, "id").text = site_url or "urn:squishmark:feed"

    # Self link
    SubElement(feed, "link", rel="self", type="application/atom+xml", href=f"{site_url}/feed.xml")
    SubElement(feed, "link", rel="alternate", type="text/html", href=site_url or "/")

    if site.author:
        author_el = SubElement(feed, "author")
        SubElement(author_el, "name").text = site.author

    # Updated = most recent post date (or now)
    if posts and posts[0].date:
        SubElement(feed, "updated").text = _rfc3339(posts[0].date)
    else:
        SubElement(feed, "updated").text = datetime.datetime.now(datetime.timezone.utc).isoformat()

    for post in posts:
        entry = SubElement(feed, "entry")
        SubElement(entry, "title").text = post.title

        post_url = f"{site_url}{post.url}"
        SubElement(entry, "id").text = post_url
        SubElement(entry, "link", rel="alternate", type="text/html", href=post_url)

        if post.date:
            SubElement(entry, "updated").text = _rfc3339(post.date)
            SubElement(entry, "published").text = _rfc3339(post.date)

        if post.author or site.author:
            entry_author = SubElement(entry, "author")
            SubElement(entry_author, "name").text = post.author or site.author

        if post.description:
            SubElement(entry, "summary").text = post.description

        # Include full HTML content
        content_el = SubElement(entry, "content", type="html")
        content_el.text = post.html

    return b'<?xml version="1.0" encoding="utf-8"?>\n' + tostring(feed, encoding="unicode").encode("utf-8")


FEED_CACHE_KEY = "feed:atom"


@router.get("/feed.xml")
async def atom_feed() -> Response:
    """Serve the Atom 1.0 feed."""
    cache = get_cache()

    # Return cached feed if available
    cached_xml = await cache.get(FEED_CACHE_KEY)
    if cached_xml is not None:
        return Response(content=cached_xml, media_type="application/atom+xml; charset=utf-8")

    github_service = get_github_service()
    config_data = await github_service.get_config()
    config = Config.from_dict(config_data)
    markdown_service = get_markdown_service(config)

    # Fetch all published posts
    post_files = await github_service.list_directory("posts")
    posts: list[Post] = []
    for path in post_files:
        if not path.endswith(".md"):
            continue
        file = await github_service.get_file(path)
        if file is None:
            continue
        post = markdown_service.parse_post(path, file.content)
        if not post.draft:
            posts.append(post)

    # Newest first
    posts.sort(key=lambda p: (p.date is not None, p.date), reverse=True)

    # Limit to 20 most recent
    posts = posts[:20]

    xml_bytes = _build_atom_feed(config, posts)
    await cache.set(FEED_CACHE_KEY, xml_bytes)
    return Response(content=xml_bytes, media_type="application/atom+xml; charset=utf-8")
