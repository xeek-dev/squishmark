# CLAUDE.md - SquishMark

SquishMark is a lightweight, GitHub-powered blogging engine. Content lives in a separate GitHub repo and is fetched at runtime. Themes use Jinja2 templates.

## Skills

**INSTRUCTION:** If your task involves any of these domains, invoke the relevant skill using `Skill(skill-name)`.

| Skill | Description |
|-------|-------------|
| `python` | Python coding standards (FastAPI, SQLAlchemy, Pydantic, async patterns) |
| `docker` | Dockerfile standards (hatchling builds, multi-stage patterns) |
| `playwright-cli` | Browser testing with Playwright (navigation, screenshots, verification) |
| `github` | GitHub operations via gh CLI (issues, PRs, labels, milestones, GraphQL) |
| `git` | Git conventions (conventional commits, branch naming, commit messages) |
| `theme-creator` | Theme authoring — templates, variables, filters, static files |
| `dev-setup` | Dev environment, scripts, configuration, deployment |

## Planning Workflow

When planning implementation work, follow this workflow:

1. **Git Setup**
   - Switch to main branch and fetch/pull latest changes
   - Prompt about GitHub issue tracking:
     - "Should we use an existing GitHub issue, create a new one, or skip issue tracking?"
     - If existing: ask for issue number
     - If new: create issue with appropriate title/description
   - Prompt about branch creation:
     - "Should we create a new branch for this work?"
     - Use **Conventional Commits style prefixes** matching the anticipated merge commit
     - Format: `type/issue-description`
     - Examples:
       - `feat/42-user-authentication`
       - `fix/15-header-overflow`
       - `refactor/16-theme-subpackage`
       - `chore/23-update-dependencies`
       - `docs/8-api-documentation`

2. **Implementation**
   - Follow the approved plan
   - Don't duplicate code — extract shared utilities immediately
   - Write tests for new functionality (don't just fix broken existing tests)
   - Run `python scripts/run-checks.py` (format, lint, pytest, pyright) — see `dev-setup` skill for options

3. **Verification**
   - Start dev server with `python scripts/start-dev.py` (or `-b` for background) — see `dev-setup` skill for options
   - Manually verify changes work with Playwright (`playwright-cli`)
   - Test all bundled themes: default, blue-tech, terminal
   - Test both positive and negative cases (e.g. admin vs anonymous, with data vs empty)
   - Don't state facts without verifying (check files exist, check CI status, etc.)

4. **PR Workflow**
   - Commit messages and PR titles **must** use [Conventional Commits](https://www.conventionalcommits.org/) format: `type(scope): description`
     - Examples: `feat(terminal): add pixel art title renderer`, `fix(docs): correct cache-busting instructions`
     - Use the same `type` as the branch prefix; `scope` is optional but recommended
   - Commit and push changes
   - Create PR linked to the issue
   - Wait for CI checks to pass
   - If checks fail: fix issues, commit, add brief PR comment about the fix, repeat

## GitHub Interaction

For all GitHub operations (issues, PRs, labels, milestones), use the `github` skill. If `gh` commands fail with auth errors, run `gh auth login`.

When commenting on PRs or issues, always sign with `*— Claude*`.

## Development

### Running Tests

```bash
pytest
```

### Docker Build

```bash
docker build -t squishmark .
docker run -p 8000:8000 -e GITHUB_CONTENT_REPO=user/repo squishmark
```
