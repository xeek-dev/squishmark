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

Present only when the post belongs to a series. Guard rendering with `{% if post.series %}` and treat the rest defensively. All sort by `series_order` (nulls last), then date.

| Variable | Type | Description |
|----------|------|-------------|
| `series_posts` | `list[Post] \| None` | All posts in the series, ordered. Drafts are included only for admins. |
| `series_index` | `int \| None` | 1-based position of the current post in the series. |
| `series_total` | `int \| None` | Total number of posts in the series. |
| `series_prev` | `Post \| None` | Previous post in the series (`None` on the first post). |
| `series_next` | `Post \| None` | Next post in the series (`None` on the last post). |
