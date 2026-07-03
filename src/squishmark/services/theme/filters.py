"""Custom Jinja2 filters for SquishMark templates."""

import re
from typing import Any
from urllib.parse import quote

from jinja2 import Environment
from markupsafe import Markup, escape


def format_date(value: Any, fmt: str = "%B %d, %Y") -> str:
    """Format a date object."""
    if value is None:
        return ""
    if hasattr(value, "strftime"):
        return value.strftime(fmt)
    return str(value)


def accent_first_word(value: str) -> Markup:
    """Wrap the first word in an accent span for styling.

    Multi-word titles accent the first whitespace-delimited word. A single-word
    CamelCase title (e.g. ``SquishMark``) is split on its last interior
    uppercase boundary so it renders two-tone (``Squish`` accented, ``Mark``
    plain), matching the navbar logo; a single lowercase word falls back to
    accenting the whole word.
    """
    if not value:
        return Markup("")
    words = value.split(" ", 1)
    if len(words) == 1:
        word = words[0]
        interior_caps = [m.start() for m in re.finditer(r"[A-Z]", word) if m.start() > 0]
        if interior_caps:
            split = interior_caps[-1]
            return Markup(f'<span class="accent">{escape(word[:split])}</span>{escape(word[split:])}')
        return Markup(f'<span class="accent">{escape(word)}</span>')
    return Markup(f'<span class="accent">{escape(words[0])}</span> {escape(words[1])}')


def accent_last_word(value: str) -> Markup:
    """Wrap the last word in an accent span for styling."""
    if not value:
        return Markup("")
    words = value.rsplit(" ", 1)
    if len(words) == 1:
        return Markup(f'<span class="accent">{escape(words[0])}</span>')
    return Markup(f'{escape(words[0])} <span class="accent">{escape(words[1])}</span>')


def share_urls(post: Any, canonical_url: str | None) -> list[tuple[str, str]]:
    """Build (platform, share_url) pairs for a post.

    Takes the absolute post URL (canonical_url from the render context) and
    returns direct share links with the URL and title percent-encoded.
    Returns an empty list when canonical_url is falsy (site.url unset) so
    templates can hide the share section entirely.
    """
    if not canonical_url:
        return []
    url = quote(canonical_url, safe="")
    title = quote(getattr(post, "title", "") or "", safe="")
    return [
        ("Twitter/X", f"https://twitter.com/intent/tweet?url={url}&text={title}"),
        ("LinkedIn", f"https://www.linkedin.com/sharing/share-offsite/?url={url}"),
        ("Facebook", f"https://www.facebook.com/sharer/sharer.php?u={url}"),
        ("Reddit", f"https://reddit.com/submit?url={url}&title={title}"),
        ("Hacker News", f"https://news.ycombinator.com/submitlink?u={url}&t={title}"),
        ("Email", f"mailto:?subject={title}&body={url}"),
    ]


def register_filters(env: Environment) -> None:
    """Register all custom filters on a Jinja2 environment."""
    env.filters["format_date"] = format_date
    env.filters["accent_first_word"] = accent_first_word
    env.filters["accent_last_word"] = accent_last_word
    env.filters["share_urls"] = share_urls
