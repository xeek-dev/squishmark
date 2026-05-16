---
name: github
description: GitHub operations via gh CLI (issues, PRs, labels, milestones, GraphQL)
---

# GitHub Operations

Use the `gh` CLI for all GitHub operations. Run individual `gh` commands via the Bash tool — do not use shell loops or compound scripts. Make parallel tool calls for independent operations.

## Command Execution Rules

- **One `gh` command per Bash call** — no shell loops, pipes between gh commands, or multi-step scripts
- **Parallel tool calls** for independent operations (e.g., creating labels + setting milestone)
- **HEREDOC for multi-line bodies** — always use HEREDOC syntax for issue/PR bodies:
  ```bash
  gh issue create --title "Title" --body "$(cat <<'EOF'
  Multi-line body here.

  - Detail 1
  - Detail 2
  EOF
  )"
  ```

## API Selection

| Task | Tool | Example |
|------|------|---------|
| Standard CRUD (issues, PRs, labels) | `gh issue`, `gh pr`, `gh label` | `gh issue create --title "Bug"` |
| Fields not exposed by CLI (issue types, sub-issues) | `gh api graphql` | See `references/graphql.md` |
| Simple REST endpoints | `gh api` | `gh api repos/{owner}/{repo}/milestones` |

## Issues

### Creation Flow

A complete issue has **title + body + labels + milestone + type**. Don't ship partial issues.

1. Search for duplicates: `gh issue list --search "keyword" --state all`
2. Create with title, body, labels in one call:
   ```bash
   gh issue create --title "..." --label "engine,enhancement" --body "$(cat <<'EOF'
   ...
   EOF
   )"
   ```
3. Set milestone (default `SquishMark 1.0`; only ask if multiple are active):
   `gh issue edit <num> --milestone "SquishMark 1.0"`
4. Set type (`Feature`/`Bug`/`Task`):
   ```bash
   python .claude/skills/github/scripts/github-issue-updater.py <num> --type feature
   ```
   Or via GraphQL — see `references/graphql.md`.

See `references/labels.md` and `references/milestones.md` for available values.

### Edit and Search

```bash
gh issue edit 42 --title "New title"
gh issue list
gh issue list --search "label:bug sort:updated-desc"
```

## Pull Requests

See `references/pull-requests.md` for create, review, comment, merge, and Copilot review commands.

## Conventions

### Comment Signing

Always sign comments on PRs and issues so it is clear they are AI-generated:

```
Your comment text here.

*— Claude*
```

For git conventions (conventional commits, branch naming), see the `git` skill.

## Auth Troubleshooting

If `gh` commands fail with auth errors:

```bash
gh auth login
gh auth status
```
