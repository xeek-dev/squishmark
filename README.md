# SquishMark

A lightweight, GitHub-powered blogging engine with Jinja2 theming.

**Status:** In development

## What is SquishMark?

SquishMark is a blogging platform that fetches your content from a GitHub repository and renders it as a website. Write your posts in Markdown, push to GitHub, and your blog updates automatically.

### Key Features

- **GitHub as CMS** - Your posts and pages live in a Git repo. Version control, PRs, and collaboration built-in.
- **Jinja2 Themes** - Create themes with HTML, CSS, and Jinja2 templates. No Python required.
- **Syntax Highlighting** - Server-side code highlighting with Pygments (500+ languages).
- **Simple Deployment** - Deploy to Fly.io with a single command.
- **Admin Features** - GitHub OAuth login, page analytics, content notes/corrections.

## Quick Start

### 1. Create your content repository

Use the [squishmark-starter](https://github.com/xeek-dev/squishmark-starter) template to create your content repo.

### 2. Deploy SquishMark

```bash
# Clone SquishMark
git clone https://github.com/xeek-dev/squishmark.git
cd squishmark

# Deploy to Fly.io
fly launch
fly secrets set GITHUB_CONTENT_REPO=your-username/your-content-repo
fly deploy
```

### 3. Write posts

```markdown
---
title: My First Post
date: 2026-01-25
tags: [hello, world]
---

# Hello World

This is my first post written in **Markdown**.

```python
print("Hello from SquishMark!")
```
```

## Documentation

- [Getting Started Guide](docs/getting-started.md) *(coming soon)*
- [Theming Guide](docs/theming.md) *(coming soon)*
- [Configuration Reference](docs/configuration.md) *(coming soon)*
- [Deployment Guide](docs/deployment.md) *(coming soon)*

## Tech Stack

- **Python 3.11+** with FastAPI
- **Jinja2** for templating
- **Pygments** for syntax highlighting
- **SQLite** for analytics and admin features
- **Fly.io** for hosting (or any Docker-compatible platform)

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) *(coming soon)* for guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.
