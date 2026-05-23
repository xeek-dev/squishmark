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
| `post.html` | `post` (Post), `notes` (list) |
| `page.html` | `page` (Page), `notes` (list) |
| `404.html` | Global context only |
| `admin/admin.html` | `user` (dict), `analytics` (dict), `notes` (list[NoteResponse]), `cache_size` (int) |

## Useful Post fields

`post.html` is the rendered post body. A few less-obvious fields:

- `post.toc` — auto-generated table-of-contents HTML (a `<div class="toc">` wrapping a nested `<ul>`). Empty string when the post has no headings, or when the post sets `toc: false` in frontmatter. Themes opt in to render it; the three bundled themes show three different treatments (inline card, `<details>` collapsible, floating sidebar) — use them as references.
- `post.reading_time` — string like `"3 min read"`.
- `post.url` — canonical URL path (`/posts/<slug>`).
