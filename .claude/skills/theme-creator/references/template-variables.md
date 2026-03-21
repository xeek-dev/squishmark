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
