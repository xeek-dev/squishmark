# SquishMark

[![CI](https://github.com/xeek-dev/squishmark/actions/workflows/ci.yml/badge.svg)](https://github.com/xeek-dev/squishmark/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/xeek-dev/squishmark)](https://github.com/xeek-dev/squishmark/releases)
[![Python 3.14+](https://img.shields.io/badge/python-3.14+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

A lightweight, GitHub-powered blogging engine with Jinja2 theming.

**See it live:** [squishmark.dev](https://squishmark.dev) is the official site, and it runs on SquishMark itself.

**Status:** approaching [1.0](https://github.com/xeek-dev/squishmark/milestone/1)

## What is SquishMark?

SquishMark renders a website straight from a GitHub repository. Write posts in Markdown, push, and your blog updates in seconds. There is no build step and your content stays in plain files you own.

- **GitHub as CMS**: posts and pages live in a Git repo, with version control and PRs built in
- **Jinja2 themes**: three bundled, and you can reskin or override any of them from your content repo without forking the engine
- **Syntax highlighting**: server-side Pygments, 500+ languages
- **Search, tags, series, drafts, feeds, sitemaps**: blog essentials included
- **Admin features**: GitHub OAuth login, page analytics, content notes

## Quick start

1. Create your content repo from the [squishmark-starter](https://github.com/xeek-dev/squishmark-starter) template.
2. Deploy the engine and point it at your repo. The full walkthrough (including Windows commands and the push webhook) is the [getting started guide](https://squishmark.dev/docs/getting-started); the short version for Fly.io:

```bash
git clone https://github.com/xeek-dev/squishmark.git
cd squishmark
fly launch
fly volumes create squishmark_data --size 1
fly secrets set GITHUB_CONTENT_REPO=your-username/your-content-repo
fly secrets set SECRET_KEY=$(openssl rand -hex 32)
fly deploy
```

3. Write a post in your content repo's `posts/` directory and push:

````markdown
---
title: My First Post
date: 2026-01-25
tags: [hello, world]
---

Hello from **Markdown**.

```python
print("Hello from SquishMark!")
```
````

Prefer Docker? Any Docker host works; the image is published for amd64 and arm64:

```bash
docker run -d -p 8000:8000 \
  -v squishmark_data:/data \
  -e GITHUB_CONTENT_REPO=your-username/your-content-repo \
  ghcr.io/xeek-dev/squishmark:latest
```

## Documentation

Full guides live on the official site:

- [Getting started](https://squishmark.dev/docs/getting-started)
- [Configuration](https://squishmark.dev/docs/configuration): every environment variable and `config.yml` field
- [Theming](https://squishmark.dev/docs/theming)
- [Frontmatter reference](https://squishmark.dev/docs/frontmatter)

## Themes

- **default**: clean and minimal, light and dark
- **blue-tech**: dark SaaS aesthetic with electric blue accents and its own landing page
- **terminal**: terminal aesthetic with CSS pixel art titles and configurable backgrounds

Pick one in your content repo's `config.yml` (`theme: name: blue-tech`), override it per page in frontmatter, or reskin it from your own repo; the [theming guide](https://squishmark.dev/docs/theming) covers all three. There's a visual tour in [Meet the themes](https://squishmark.dev/posts/meet-the-themes).

## Development

```bash
git clone https://github.com/xeek-dev/squishmark.git
cd squishmark
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
python scripts/start-dev.py
```

The dev server installs dependencies on first run, serves the local `content/` folder as test content, and auto-reloads. Options:

```bash
python scripts/start-dev.py --host=0.0.0.0 --port=3000 --no-reload
python scripts/start-dev.py -b  # run in background (prints PID)
```

Run the same checks CI runs with `python scripts/run-checks.py`. Docker-based dev: `docker compose up --build`. Dependency updates are automated weekly via [Dependabot](.github/dependabot.yml).

## Tech stack

Python 3.14+ with FastAPI, Jinja2 templating, Pygments highlighting, and SQLite for analytics and admin features.

## Contributing

Issues and PRs are welcome.

## License

MIT License - see [LICENSE](LICENSE) for details.
