# Model Fields

## SiteConfig

| Field | Type | Description |
|-------|------|-------------|
| `title` | `str` | Site title |
| `description` | `str` | Site description |
| `author` | `str` | Site author name |
| `url` | `str` | Site URL |
| `favicon` | `str \| None` | Custom favicon path override |
| `featured_max` | `int` | Max number of featured posts returned (default: 5) |

## Post

| Field | Type | Description |
|-------|------|-------------|
| `slug` | `str` | URL slug |
| `title` | `str` | Post title |
| `date` | `datetime.date \| None` | Publication date |
| `tags` | `list[str]` | Tag list |
| `description` | `str` | Short description / excerpt |
| `content` | `str` | Raw markdown content |
| `html` | `str` | Rendered HTML content |
| `draft` | `bool` | Draft flag |
| `featured` | `bool` | Whether the post is featured |
| `featured_order` | `int \| None` | Sort order within featured posts (lower = first, nulls last) |
| `template` | `str \| None` | Custom template override |
| `theme` | `str \| None` | Per-post theme override |
| `author` | `str \| None` | Post author (overrides site author) |
| `url` | `str` | Computed URL (property) — e.g. `/posts/my-post` |

## Page

| Field | Type | Description |
|-------|------|-------------|
| `slug` | `str` | URL slug |
| `title` | `str` | Page title |
| `content` | `str` | Raw markdown content |
| `html` | `str` | Rendered HTML content |
| `template` | `str \| None` | Custom template override |
| `theme` | `str \| None` | Per-page theme override |
| `url` | `str` | Computed URL (property) — e.g. `/about` |

## Pagination

| Field | Type | Description |
|-------|------|-------------|
| `page` | `int` | Current page number |
| `per_page` | `int` | Items per page |
| `total_items` | `int` | Total number of posts |
| `total_pages` | `int` | Total number of pages |
| `has_prev` | `bool` | Whether a previous page exists (property) |
| `has_next` | `bool` | Whether a next page exists (property) |
| `prev_page` | `int \| None` | Previous page number (property) |
| `next_page` | `int \| None` | Next page number (property) |
