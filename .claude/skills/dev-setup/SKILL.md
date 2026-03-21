---
name: dev-setup
description: Development environment setup, scripts, configuration, and deployment for SquishMark
---

# Development Environment

## Local Setup

```bash
# Clone the repo
git clone https://github.com/xeek-dev/squishmark.git
cd squishmark

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install dependencies
pip install -e ".[dev]"

# Run locally
uvicorn squishmark.main:app --reload
```

## Development Scripts

Two user-facing scripts in `scripts/` and two agent-facing scripts in skill directories:

### Environment Check

Run the readiness check before starting work:

```bash
python .claude/skills/dev-setup/scripts/check-env.py
```

### User-Facing Scripts (`scripts/`)

### `start-dev.py` — Dev server with multi-server management

Starts a uvicorn dev server pointing at the local `content/` directory. Supports running multiple named server instances simultaneously (tracked in `.dev-servers.json`). The default instance name is the current git branch.

```bash
# Basic usage
python scripts/start-dev.py                     # foreground on :8000
python scripts/start-dev.py -b                  # background on :8000
python scripts/start-dev.py -b --port 8001      # background on :8001
python scripts/start-dev.py --name api -b       # named background instance

# Server management
python scripts/start-dev.py --list              # show all tracked servers
python scripts/start-dev.py --stop              # stop current branch's server
python scripts/start-dev.py --stop api          # stop named server
python scripts/start-dev.py --stop 12345        # stop server by PID
python scripts/start-dev.py --stop-all          # stop all servers
python scripts/start-dev.py --restart -b        # restart in background

# Other options
python scripts/start-dev.py --host 0.0.0.0     # bind to all interfaces
python scripts/start-dev.py --no-reload         # disable auto-reload
```

> **Stale port gotcha:** Background start (`-b`) can silently fail if a stale process holds the port. The old process keeps serving while the new one exits. Always verify after restart: `--stop <name>` then `lsof -ti:<port> | xargs kill` before starting fresh.

### `run-checks.py` — Local CI checks

Runs the same checks as CI: **ruff format**, **ruff check**, **pytest**, and **pyright**. By default runs all checks and reports a summary.

```bash
python scripts/run-checks.py                    # run all checks
python scripts/run-checks.py --fail-fast        # stop on first failure
python scripts/run-checks.py --docker           # also run docker build (slow)
```

### Agent-Facing Scripts (in skill directories)

#### `setup-worktree.py` — Git worktree management (in `git` skill)

Creates isolated worktrees in `.worktrees/` for parallel development.

```bash
python .claude/skills/git/scripts/setup-worktree.py feat/42-dark-mode                # create worktree + branch
python .claude/skills/git/scripts/setup-worktree.py feat/42-dark-mode --install      # also pip install -e
python .claude/skills/git/scripts/setup-worktree.py feat/42-dark-mode --with-content # also copy content/
python .claude/skills/git/scripts/setup-worktree.py feat/42-dark-mode --integration  # --install + --with-content
python .claude/skills/git/scripts/setup-worktree.py --list                           # list active worktrees
python .claude/skills/git/scripts/setup-worktree.py --cleanup 42-dark-mode           # remove worktree + branch
```

#### `github-issue-updater.py` — Issue metadata updater (in `github` skill)

Sets issue type (task/bug/feature), adds labels, and assigns milestones in a single command.

```bash
python .claude/skills/github/scripts/github-issue-updater.py 42 --type task
python .claude/skills/github/scripts/github-issue-updater.py 42 --add-label "engine,themes"
python .claude/skills/github/scripts/github-issue-updater.py 42 --milestone "SquishMark 1.0"
```

## Configuration

### Environment Variables

```bash
# Required
GITHUB_CONTENT_REPO=xeek-dev/xeek-dev-content
GITHUB_TOKEN=ghp_...  # Only for private repos

# Optional
CACHE_TTL_SECONDS=300
DATABASE_URL=sqlite:///data/squishmark.db

# GitHub OAuth (for admin features)
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...
```

### config.yml (in content repo)

```yaml
site:
  title: "My Blog"
  description: "A blog about things"
  author: "Your Name"
  url: "https://example.com"
  favicon: "/static/user/custom-icon.png"  # Optional: override auto-detected favicon
  featured_max: 5                           # Optional: max featured posts (default: 5)

theme:
  name: default
  pygments_style: monokai

posts:
  per_page: 10
```

## Deployment (Fly.io)

```bash
# First time
fly launch

# Create volume for SQLite
fly volumes create squishmark_data --size 1

# Set secrets
fly secrets set GITHUB_TOKEN=ghp_...
fly secrets set GITHUB_CLIENT_ID=...
fly secrets set GITHUB_CLIENT_SECRET=...

# Deploy
fly deploy
```

## Common Tasks

### Adding a new route
1. Create router in `src/squishmark/routers/`
2. Register in `main.py`
3. Add corresponding Jinja2 template if needed

### Testing with a local content repo
Set `GITHUB_CONTENT_REPO` to a local path (prefixed with `file://`) for development without GitHub API calls.
