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

1. **Search for duplicates** before creating:
   ```bash
   gh issue list --search "keyword" --state all
   ```

2. **Create the issue:**
   ```bash
   gh issue create --title "Add dark mode" --body "$(cat <<'EOF'
   ## Description
   Add dark mode support.

   ## Acceptance Criteria
   - Toggle in settings
   - Persists across sessions
   EOF
   )" --label "enhancement"
   ```

3. **Set issue type** — see `references/graphql.md` for GraphQL mutations, or use the helper script:
   ```bash
   python .claude/skills/github/scripts/github-issue-updater.py 42 --type task
   ```

4. **Apply labels:** `gh issue edit 42 --add-label "engine,enhancement"` — see `references/labels.md`

5. **Prompt about milestone** — ask the user. See `references/milestones.md`

### Edit and Search

```bash
gh issue edit 42 --title "New title"
gh issue list
gh issue list --search "label:bug sort:updated-desc"
```

## Pull Requests

See `references/pull-requests.md` for create, review, comment, and merge commands.

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
