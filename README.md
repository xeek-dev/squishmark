# SquishMark

[![CI](https://github.com/xeek-dev/squishmark/actions/workflows/ci.yml/badge.svg)](https://github.com/xeek-dev/squishmark/actions/workflows/ci.yml)
[![Python 3.14+](https://img.shields.io/badge/python-3.14+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

A lightweight, GitHub-powered blogging engine with Jinja2 theming.

**Status:** In development

## What is SquishMark?

SquishMark is a blogging platform that fetches your content from a GitHub repository and renders it as a website. Write your posts in Markdown, push to GitHub, and your blog updates automatically.

### Key Features

- **GitHub as CMS** - Your posts and pages live in a Git repo. Version control, PRs, and collaboration built-in.
- **Jinja2 Themes** - Create themes with HTML, CSS, and Jinja2 templates. No Python required.
- **Syntax Highlighting** - Server-side code highlighting with Pygments (500+ languages).
- **Simple Deployment** - Deploy to Fly.io or any Docker host.
- **Admin Features** - GitHub OAuth login, page analytics, content notes/corrections.

### Contents

- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Themes](#themes)
- [Development](#development)
- [Tech Stack](#tech-stack)
- [Contributing](#contributing)

## Quick Start

### 1. Create your content repository

Use the [squishmark-starter](https://github.com/xeek-dev/squishmark-starter) template to create your content repo.

### 2. Deploy SquishMark

Choose your deployment method:

#### Option A: Fly.io (Recommended)

The easiest way to get started. Fly.io offers a free tier that works great for personal blogs.

```bash
# Install Fly CLI: https://fly.io/docs/hands-on/install-flyctl/

# Clone SquishMark
git clone https://github.com/xeek-dev/squishmark.git
cd squishmark

# Launch on Fly.io
fly launch

# Create a volume for the database
fly volumes create squishmark_data --size 1

# Set your content repo
fly secrets set GITHUB_CONTENT_REPO=your-username/your-content-repo

# For private content repos, add a GitHub token
fly secrets set GITHUB_TOKEN=ghp_your_token_here

# Deploy
fly deploy
```

#### Option B: Docker

Run SquishMark anywhere Docker is supported (DigitalOcean, Linode, AWS, your own server, etc.)

```bash
# Pull the image
docker pull ghcr.io/xeek-dev/squishmark:latest

# Run with environment variables
docker run -d \
  --name squishmark \
  -p 8000:8000 \
  -v squishmark_data:/data \
  -e GITHUB_CONTENT_REPO=your-username/your-content-repo \
  -e GITHUB_TOKEN=ghp_your_token_here \
  ghcr.io/xeek-dev/squishmark:latest
```

Or use Docker Compose:

```yaml
# docker-compose.yml
services:
  squishmark:
    image: ghcr.io/xeek-dev/squishmark:latest
    ports:
      - "8000:8000"
    volumes:
      - squishmark_data:/data
    environment:
      - GITHUB_CONTENT_REPO=your-username/your-content-repo
      - GITHUB_TOKEN=ghp_your_token_here  # Only for private repos

volumes:
  squishmark_data:
```

```bash
docker-compose up -d
```

### 3. Write posts

Create markdown files in your content repo's `posts/` directory:

```markdown
---
title: My First Post
date: 2026-01-25
tags: [hello, world]
featured: true        # Optional: include in featured_posts context
featured_order: 1     # Optional: sort order (lower = first)
---

# Hello World

This is my first post written in **Markdown**.

```python
print("Hello from SquishMark!")
```
```

Push to GitHub, and your blog updates automatically.

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GITHUB_CONTENT_REPO` | Yes | Your content repo (e.g., `username/my-blog-content`) |
| `GITHUB_TOKEN` | For private repos | GitHub personal access token |
| `CACHE_TTL_SECONDS` | No | How long to cache content (default: 300) |
| `DATABASE_URL` | No | SQLite path (default: `/data/squishmark.db`) |

### Content Repository Config

Create a `config.yml` in your content repo:

```yaml
site:
  title: "My Blog"
  description: "A blog about things"
  author: "Your Name"
  url: "https://yourdomain.com"
  favicon: "/static/user/custom-icon.png"  # Optional
  featured_max: 5                           # Optional: max featured posts (default: 5)

theme:
  name: default
  pygments_style: monokai

posts:
  per_page: 10
```

### Favicon

Add a favicon by placing `favicon.ico`, `favicon.png`, or `favicon.svg` in your content repo's `static/` directory:

```
my-content-repo/
├── posts/
├── pages/
├── static/
│   └── favicon.ico    # Auto-detected
└── config.yml
```

The favicon is automatically detected and served at `/favicon.ico`.

## Documentation

- [Getting Started Guide](docs/getting-started.md) *(coming soon)*
- [Theming Guide](docs/theming.md) *(coming soon)*
- [Configuration Reference](docs/configuration.md) *(coming soon)*

## Themes

SquishMark includes bundled themes:

- **default** - Clean, minimal design
- **blue-tech** - Dark SaaS aesthetic with electric blue accents, frosted glass nav, and hero section
- **terminal** - Dark terminal aesthetic with CSS pixel art titles, 9 configurable backgrounds, and custom syntax highlighting

Set your theme in `config.yml`:

```yaml
theme:
  name: blue-tech
  pygments_style: nord
```

You can also override the theme per-page using frontmatter:

```yaml
---
title: Special Page
theme: default  # Use default theme for just this page
---
```

## Development

### Quick Start

```bash
# Clone the repo
git clone https://github.com/xeek-dev/squishmark.git
cd squishmark

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Start development server (auto-installs dependencies)
python scripts/start-dev.py
```

The dev server:
- Installs dependencies from `pyproject.toml` if missing
- Uses local `content/` folder for test content
- Creates `data/` directory for SQLite database
- Runs with auto-reload enabled

### Options

```bash
python scripts/start-dev.py --host=0.0.0.0 --port=3000 --no-reload
python scripts/start-dev.py -b  # run in background (prints PID)
```

### Running with Docker

```bash
docker compose up --build
```

## Tech Stack

- **Python 3.14+** with FastAPI
- **Jinja2** for templating
- **Pygments** for syntax highlighting
- **SQLite** for analytics and admin features

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) *(coming soon)* for guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.
