# Jinja2 Filters

| Filter | Signature | Description |
|--------|-----------|-------------|
| `format_date` | `format_date(value, fmt="%B %d, %Y")` | Formats a date — e.g. `{{ post.date \| format_date }}` |
| `accent_first_word` | `accent_first_word(value)` | Wraps first word in `<span class="accent">` |
| `accent_last_word` | `accent_last_word(value)` | Wraps last word in `<span class="accent">` |

All accent filters return `Markup` (safe HTML).
