---
name: theme-creator
description: SquishMark theme authoring — templates, variables, filters, static files
---

# Theme Authoring Guide

## Theme Structure

Each theme lives in `themes/{name}/` with this layout:

```
themes/{name}/
├── base.html          # Base layout (required)
├── index.html         # Post listing / homepage (required)
├── post.html          # Single post (required)
├── page.html          # Single page (required)
├── 404.html           # Not found page (required)
├── admin/
│   └── admin.html     # Admin dashboard (optional, standalone — does NOT extend base.html)
└── static/
    ├── style.css      # Theme styles
    └── pygments.css   # Syntax highlighting styles
```

## Template Variables

`site` and `theme` are populated from the content repository's `config.yml`.

### Global (available in all templates)

| Variable | Type | Description |
|----------|------|-------------|
| `site` | `SiteConfig` | Site-wide configuration from `config.yml` |
| `theme` | `ThemeConfig` | Theme configuration from `config.yml` |
| `theme_name` | `str` | Active theme name (e.g. `"terminal"`) |
| `favicon_url` | `str \| None` | Resolved favicon URL, if any |

### Per-Template Context

| Template | Additional Variables |
|----------|---------------------|
| `index.html` | `posts` (list[Post]), `pagination` (Pagination), `notes` (list) |
| `post.html` | `post` (Post), `notes` (list) |
| `page.html` | `page` (Page), `notes` (list) |
| `404.html` | Global context only |
| `admin/admin.html` | `user` (dict), `analytics` (dict), `notes` (list[NoteResponse]), `cache_size` (int) |

## Model Fields

### SiteConfig

| Field | Type | Description |
|-------|------|-------------|
| `title` | `str` | Site title |
| `description` | `str` | Site description |
| `author` | `str` | Site author name |
| `url` | `str` | Site URL |
| `favicon` | `str \| None` | Custom favicon path override |

### Post

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
| `template` | `str \| None` | Custom template override |
| `theme` | `str \| None` | Per-post theme override |
| `author` | `str \| None` | Post author (overrides site author) |
| `url` | `str` | Computed URL (property) — e.g. `/posts/my-post` |

### Page

| Field | Type | Description |
|-------|------|-------------|
| `slug` | `str` | URL slug |
| `title` | `str` | Page title |
| `content` | `str` | Raw markdown content |
| `html` | `str` | Rendered HTML content |
| `template` | `str \| None` | Custom template override |
| `theme` | `str \| None` | Per-page theme override |
| `url` | `str` | Computed URL (property) — e.g. `/about` |

### Pagination

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

## Template Inheritance

Templates extend `base.html` using Jinja2 inheritance:

```jinja2
{% extends "base.html" %}

{% block title %}{{ post.title }} - {{ site.title }}{% endblock %}

{% block content %}
  {# page content here #}
{% endblock %}
```

### Available Blocks in base.html

| Block | Purpose |
|-------|---------|
| `title` | Page `<title>` tag content |
| `description` | Meta description content |
| `head` | Additional `<head>` elements (CSS, JS, meta tags) |
| `content` | Main page content |

**Note:** `admin/admin.html` is standalone and does NOT extend `base.html`.

## Jinja2 Filters

| Filter | Signature | Description |
|--------|-----------|-------------|
| `format_date` | `format_date(value, fmt="%B %d, %Y")` | Formats a date — e.g. `{{ post.date \| format_date }}` |
| `accent_first_word` | `accent_first_word(value)` | Wraps first word in `<span class="accent">` |
| `accent_last_word` | `accent_last_word(value)` | Wraps last word in `<span class="accent">` |

All accent filters return `Markup` (safe HTML).

## Static Files

### URL Patterns

| Type | URL | Source |
|------|-----|--------|
| Theme static | `/static/{theme_name}/{file_path}` | `themes/{name}/static/` |
| User static | `/static/user/{path}` | Content repo `static/` directory |

- Allowed extensions: `.ico` `.png` `.svg` `.jpg` `.jpeg` `.webp` `.gif` `.css` `.js`
- Cache-Control: `public, max-age=86400` (1 day)
- Theme static files fall back to the `default` theme if not found in the current theme

### Referencing Static Files in Templates

```jinja2
<link rel="stylesheet" href="/static/{{ theme_name }}/style.css">
<link rel="stylesheet" href="/static/{{ theme_name }}/pygments.css">
<img src="/static/user/logo.png" alt="Logo">
```

## Theme Resolution Order

When rendering a template, the engine searches in this order:

1. **Custom templates** from the content repo `/theme/` directory
2. **Current theme** from `themes/{name}/`
3. **Default theme** from `themes/default/` (fallback)

This means a theme only needs to override the templates it wants to change; missing templates fall through to the default.

## Per-Content Theme and Template Override

Individual posts and pages can override the theme or template via frontmatter:

```yaml
---
title: My Special Post
theme: terminal        # Render this post with the terminal theme
template: custom.html  # Use custom.html instead of post.html
---
```

## Pygments CSS

Generate syntax highlighting CSS for your theme:

```bash
pygmentize -S <style> -f html > themes/{name}/static/pygments.css
```

Common styles: `monokai`, `dracula`, `github-dark`, `one-dark`, `gruvbox-dark`, `nord`.

## ThemeConfig Extensibility

ThemeConfig has 5 built-in fields:

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Theme name |
| `pygments_style` | `str` | Pygments syntax highlighting style |
| `background` | `str \| None` | Background option (theme-specific) |
| `nav_image` | `str \| None` | Navigation image path |
| `hero_image` | `str \| None` | Hero section image path |

**Any extra fields** added under `theme:` in `config.yml` are accessible as `{{ theme.fieldname }}` in templates. This is enabled by `model_config = {"extra": "allow"}` on `ThemeConfig`.

Example — a theme that supports a custom accent color:

```yaml
# config.yml
theme:
  name: my-theme
  pygments_style: monokai
  accent_color: "#ff6600"
  show_sidebar: true
```

```jinja2
{# In a template #}
<style>
  :root { --accent: {{ theme.accent_color }}; }
</style>
{% if theme.show_sidebar %}
  <aside>...</aside>
{% endif %}
```
