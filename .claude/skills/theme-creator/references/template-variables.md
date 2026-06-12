# Template Variables

`site` and `theme` are populated from the content repository's `config.yml`.

## Global (available in all templates)

| Variable | Type | Description |
|----------|------|-------------|
| `site` | `SiteConfig` | Site-wide configuration from `config.yml` |
| `theme` | `ThemeConfig` | Theme configuration from `config.yml` |
| `theme_name` | `str` | Active theme name (e.g. `"terminal"`) |
| `favicon_url` | `str \| None` | Resolved favicon URL, if any |
| `featured_posts` | `list[Post]` | Featured posts, sorted and limited by `site.featured_max` (always present, may be empty) |

## Per-Template Context

| Template | Additional Variables |
|----------|---------------------|
| `index.html` | `posts` (list[Post]), `pagination` (Pagination), `notes` (list) |
| `post.html` | `post` (Post), `notes` (list), series context (see below) |
| `page.html` | `page` (Page), `notes` (list) |
| `404.html` | Global context only |
| `admin/admin.html` | `user` (dict), `analytics` (dict), `notes` (list[NoteResponse]), `cache_size` (int) |

## Useful Post fields

`post.html` is the rendered post body. A few less-obvious fields:

- `post.toc` — auto-generated table-of-contents HTML (a `<div class="toc">` wrapping a nested `<ul>`). Empty string when the post has no headings, or when the post sets `toc: false` in frontmatter. Themes opt in to render it; the three bundled themes show three different treatments (inline card, `<details>` collapsible, floating sidebar) — use them as references.
- `post.reading_time` — string like `"3 min read"`.
- `post.url` — canonical URL path (`/posts/<slug>`).
- `post.series` — series/collection name from frontmatter (`series: "My Series"`), or `None`. Posts sharing the same (case-sensitive) name are grouped into an ordered series.
- `post.series_order` — integer position within the series from frontmatter (`series_order: 2`); lower sorts first, `None`/unordered sorts last (date breaks ties). Malformed values coerce to `None`.

## Series context (post.html only)

These five variables are **always present** in the post-template context, but they are all `None` when the post does not belong to a series. Theme authors must therefore guard rendering with `{% if post.series %}` and treat the individual variables defensively. Lists sort by `series_order` (nulls last), then date.

| Variable | Type | Description |
|----------|------|-------------|
| `series_posts` | `list[Post] \| None` | All posts in the series, ordered. Drafts are included only for admins. |
| `series_index` | `int \| None` | 1-based position of the current post in the series. |
| `series_total` | `int \| None` | Total number of posts in the series. |
| `series_prev` | `Post \| None` | Previous post in the series (`None` on the first post). |
| `series_next` | `Post \| None` | Next post in the series (`None` on the last post). |

## Search component

Navbar search is a shared partial + shared JS, adopted per theme:

```jinja2
{% set search_mode = "button" %}   {# or "input" #}
{% include "_search.html" %}
```

- `button` mode: an icon button (`.search-toggle`) opens a dropdown containing the input and results (default, terminal).
- `input` mode: the input sits inline in the navbar; the dropdown shows results only (blue-tech).
- Behavior (debounced `GET /search?q=`, `Cmd/Ctrl+K`, Escape, click-outside, arrow keys) comes from `search.js` — load it with `<script src="/static/{{ theme_name }}/search.js" defer></script>` (resolves via the default-theme static fallback).
- Themes must style the hooks: `.search`, `.search-toggle`, `.search-input`, `.search-dropdown`, `.search-results` (+ `.search-result-title/-meta/-draft/-excerpt`, `.search-empty`, and `li.is-active` for keyboard highlight). See the three bundled themes for reference treatments.
- Override the markup per theme by shipping your own `_search.html`, or per site via `theme/_search.html` in the content repo; override behavior by shipping your own `static/search.js`.
