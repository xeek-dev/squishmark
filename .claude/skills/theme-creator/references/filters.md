# Jinja2 Filters

| Filter | Signature | Description |
|--------|-----------|-------------|
| `format_date` | `format_date(value, fmt="%B %d, %Y")` | Formats a date — e.g. `{{ post.date \| format_date }}` |
| `accent_first_word` | `accent_first_word(value)` | Wraps first word in `<span class="accent">` |
| `accent_last_word` | `accent_last_word(value)` | Wraps last word in `<span class="accent">` |
| `share_urls` | `share_urls(post, canonical_url)` | `(platform, url)` share link pairs; empty list when `canonical_url` is unset. Usage: `{% for platform, url in post \| share_urls(canonical_url) %}` |

All accent filters return `Markup` (safe HTML).

Themes get share buttons by including the shared partial (falls back to the default theme): `{% include "_share.html" %}`. Set `share_label` beforehand to override the "Share" label.
