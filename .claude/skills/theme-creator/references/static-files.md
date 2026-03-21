# Static Files

## URL Patterns

| Type | URL | Source |
|------|-----|--------|
| Theme static | `/static/{theme_name}/{file_path}` | `themes/{name}/static/` |
| User static | `/static/user/{path}` | Content repo `static/` directory |

- Allowed extensions: `.ico` `.png` `.svg` `.jpg` `.jpeg` `.webp` `.gif` `.css` `.js`
- Cache-Control: `public, max-age=86400` (1 day)
- Theme static files fall back to the `default` theme if not found in the current theme

## Referencing Static Files in Templates

```jinja2
<link rel="stylesheet" href="/static/{{ theme_name }}/style.css">
<link rel="stylesheet" href="/static/{{ theme_name }}/pygments.css">
<img src="/static/user/logo.png" alt="Logo">
```
