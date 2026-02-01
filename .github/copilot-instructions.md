# SquishMark - Copilot Instructions

SquishMark is a lightweight, GitHub-powered blogging engine built with FastAPI. Content lives in a separate GitHub repository and is fetched at runtime. Themes use Jinja2 templates.

## Tool Execution

When the user asks you to do something, ACTUALLY DO IT. Do NOT just show commands or suggest what to run — execute the tools and commands yourself. Use MCP tools, run terminal commands, read files, and take action directly. Only show commands without executing if the user explicitly asks "how would I..." or "what command..."

NEVER fabricate or hallucinate tool output. If you run a command or use a tool, show the ACTUAL results returned. Do NOT make up issue titles, file contents, or command output. If a tool fails or you cannot access something, say so honestly.

## Tech Stack

- Python 3.14 with type hints REQUIRED on all functions
- FastAPI (async framework)
- SQLAlchemy with aiosqlite for async database access
- Jinja2 for templating
- httpx for async HTTP calls
- python-markdown + Pygments for server-side syntax highlighting

## Project Structure

```
src/squishmark/
├── main.py              # FastAPI app entry point
├── config.py            # Pydantic settings
├── dependencies.py      # FastAPI dependency injection
├── routers/             # Route handlers (posts, pages, admin, auth, webhooks)
├── services/            # Business logic (github, markdown, cache, theme/)
└── models/              # Pydantic models (content.py) and SQLAlchemy (db.py)

themes/default/          # Bundled Jinja2 theme templates
tests/                   # pytest tests
```

## CRITICAL Coding Standards

ALWAYS use async/await - this is an async codebase. NEVER use blocking I/O calls.

ALWAYS add type hints to function signatures. Use `from __future__ import annotations` at the top of new files.

NEVER use `datetime.now()` or `datetime.utcnow()`. ALWAYS use `datetime.now(UTC)` from `datetime` module with explicit timezone.

SQLAlchemy queries MUST use the 2.0 style:
```python
# CORRECT
result = await session.execute(select(Model).where(Model.id == id))
item = result.scalar_one_or_none()

# WRONG - Do NOT use legacy 1.x patterns
session.query(Model).filter_by(id=id).first()
```

For HTTP requests, use `httpx.AsyncClient` - NEVER use `requests` library.

Pydantic models go in `models/content.py`. SQLAlchemy ORM models go in `models/db.py`. Do NOT mix them.

## Dependency Injection

Use FastAPI's `Depends()` for services. Check `dependencies.py` for existing patterns:
```python
async def my_route(
    github_service: GitHubService = Depends(get_github_service),
    cache: CacheService = Depends(get_cache_service),
):
```

## Adding Routes

1. Create router in `src/squishmark/routers/`
2. Register in `main.py` with `app.include_router()`
3. Add Jinja2 template in `themes/default/` if rendering HTML

## Testing & Verification

This project follows Test-Driven Development (TDD). You MUST write tests BEFORE writing implementation code.

**TDD Workflow — Follow this order EXACTLY:**

1. **Write the test FIRST** — STOP. Do NOT write any implementation code yet. Create a test file and write a failing test that defines the expected behavior.
2. **Run pytest** — Execute `pytest` and confirm the test FAILS. If it passes, your test is wrong.
3. **Write MINIMAL implementation** — Write only enough code to make the test pass. No extra features, no "while I'm here" additions.
4. **Run pytest again** — Confirm the test now PASSES.
5. **Refactor if needed** — Clean up while keeping tests green.

NEVER write implementation code without a corresponding test. NEVER write the implementation first and tests after.

Tests go in `tests/` directory. Match the source structure:
- `src/squishmark/services/cache.py` → `tests/services/test_cache.py`
- `src/squishmark/routers/posts.py` → `tests/routers/test_posts.py`

Run before committing:
```bash
pytest                    # Run tests
ruff check .              # Linting
ruff format .             # Formatting
```

Start dev server for manual testing:
```bash
python scripts/start-dev.py
```

## GitHub Interaction

For all GitHub operations (issues, PRs, comments, reviews), use this priority order:

1. **GitHub MCP Server** (PREFERRED) — Use MCP tools when available
2. **`gh` CLI** (FALLBACK) — Use if MCP tools fail or are unavailable
3. **Manual Setup Required** — If both fail with auth errors, tell the developer:
   ```bash
   # For gh CLI
   gh auth login

   # For MCP server, ensure GitHub MCP is configured in VS Code settings
   ```

When commenting on PRs or issues, ALWAYS sign your comments so it's clear they're AI-generated:
```
Your comment text here.

*— GitHub Copilot*
```

## Environment Variables

Required: `GITHUB_CONTENT_REPO` (e.g., `user/repo`)
Optional: `GITHUB_TOKEN` (for private repos), `CACHE_TTL_SECONDS`, `DATABASE_URL`

## Key Patterns

Content is fetched from GitHub and cached in memory. The cache service handles TTL expiration.

Theme resolution: custom theme in content repo `/theme/` takes priority over bundled `themes/default/`.

Database (SQLite) stores analytics, notes, and sessions - NOT content. Content lives in GitHub.

All markdown rendering happens server-side via Pygments. No client-side syntax highlighting.
