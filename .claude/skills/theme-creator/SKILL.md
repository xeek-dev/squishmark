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

For template variables, model fields, filters, and other reference material, see the `references/` directory.

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

## Content Repository Structure

Users create a content repo with this structure:

```
my-content-repo/
├── posts/
│   ├── 2026-01-01-hello-world.md
│   └── 2026-01-15-another-post.md
├── pages/
│   └── about.md
├── static/                   # User static files (favicon, images)
│   └── favicon.ico           # Auto-detected and served at /favicon.ico
├── theme/                    # Optional custom theme
│   └── ...
└── config.yml
```

### Frontmatter Format

```yaml
---
title: My Post Title
date: 2026-01-15
tags: [python, blogging]
draft: false
featured: true        # Optional: include in featured_posts template context
featured_order: 1     # Optional: sort order (lower = first, nulls last)
---

Post content in markdown...
```

## Live Reload

When running `python scripts/start-dev.py`, debug mode is enabled automatically. This activates live reload — a small script is injected before `</body>` that opens a WebSocket to `/dev/livereload`. Any change to files in `themes/` or the content repo's `theme/` directory triggers a full page reload in the browser.

No setup required — just save a template or CSS file and the browser refreshes.
