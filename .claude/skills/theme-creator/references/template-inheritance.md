# Template Inheritance

Templates extend `base.html` using Jinja2 inheritance:

```jinja2
{% extends "base.html" %}

{% block title %}{{ post.title }} - {{ site.title }}{% endblock %}

{% block content %}
  {# page content here #}
{% endblock %}
```

## Available Blocks in base.html

| Block | Purpose |
|-------|---------|
| `title` | Page `<title>` tag content |
| `description` | Meta description content |
| `head` | Additional `<head>` elements (CSS, JS, meta tags) |
| `content` | Main page content |

**Note:** `admin/admin.html` is standalone and does NOT extend `base.html`.
