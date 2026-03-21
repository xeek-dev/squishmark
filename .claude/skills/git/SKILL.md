---
name: git
description: Git conventions — conventional commits, branch naming, commit message format
---

# Git Conventions

## Conventional Commits

Commit messages and PR titles **must** use [Conventional Commits](https://www.conventionalcommits.org/) format:

```
type(scope): description
```

Types: `feat`, `fix`, `refactor`, `chore`, `docs`, `test`, `ci`

Scope is optional but recommended. Examples:
- `feat(terminal): add pixel art title renderer`
- `fix(docs): correct cache-busting instructions`
- `refactor(theme): extract loader into subpackage`
- `chore(dx): clean up permission settings`

## Branch Naming

```
type/issue-description
```

Use the same type prefix as the anticipated merge commit. Examples:
- `feat/42-dark-mode`
- `fix/15-header-overflow`
- `refactor/16-theme-subpackage`
- `chore/23-update-dependencies`
- `docs/8-api-documentation`

## Commit Messages

- Use multiple `-m` flags instead of `$()` heredoc substitution, which triggers a command-substitution security prompt
- Example: `git commit -m "fix(engine): wire notes into rendering" -m "Detailed body here." -m "Co-Authored-By: ..."`

## Issue Titles

- Use plain English descriptions, **not** conventional commit format
- Conventional commit format is only for commit messages and PR titles
