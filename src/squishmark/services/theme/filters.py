"""Custom Jinja2 filters for SquishMark templates."""

from typing import Any

from jinja2 import Environment
from markupsafe import Markup


def format_date(value: Any, fmt: str = "%B %d, %Y") -> str:
    """Format a date object."""
    if value is None:
        return ""
    if hasattr(value, "strftime"):
        return value.strftime(fmt)
    return str(value)


def accent_first_word(value: str) -> Markup:
    """Wrap the first word in an accent span for styling."""
    if not value:
        return Markup("")
    words = value.split(" ", 1)
    if len(words) == 1:
        return Markup(f'<span class="accent">{words[0]}</span>')
    return Markup(f'<span class="accent">{words[0]}</span> {words[1]}')


def accent_last_word(value: str) -> Markup:
    """Wrap the last word in an accent span for styling."""
    if not value:
        return Markup("")
    words = value.rsplit(" ", 1)
    if len(words) == 1:
        return Markup(f'<span class="accent">{words[0]}</span>')
    return Markup(f'{words[0]} <span class="accent">{words[1]}</span>')


def register_filters(env: Environment) -> None:
    """Register all custom filters on a Jinja2 environment."""
    env.filters["format_date"] = format_date
    env.filters["accent_first_word"] = accent_first_word
    env.filters["accent_last_word"] = accent_last_word
