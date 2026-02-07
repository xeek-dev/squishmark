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
| Fields not exposed by CLI (issue types, sub-issues) | `gh api graphql` | See GraphQL sections below |
| Simple REST endpoints | `gh api` | `gh api repos/{owner}/{repo}/milestones` |

## Issues

### Creation Flow

1. **Search for duplicates** before creating:
   ```bash
   gh issue list --search "keyword" --state all
   ```

2. **Create the issue:**
   ```bash
   gh issue create --title "feat: add dark mode" --body "$(cat <<'EOF'
   ## Description
   Add dark mode support.

   ## Acceptance Criteria
   - Toggle in settings
   - Persists across sessions
   EOF
   )" --label "enhancement"
   ```

3. **Set issue type** (see Issue Types section)

4. **Apply labels:**
   ```bash
   gh issue edit 42 --add-label "engine,enhancement"
   ```

5. **Prompt about milestone** — ask the user if the issue should be assigned to a milestone. Current milestone: **SquishMark 1.0**:
   ```bash
   # List milestones to get the number
   gh api repos/{owner}/{repo}/milestones --jq '.[].title'

   # Assign milestone by title
   gh issue edit 42 --milestone "SquishMark 1.0"
   ```

### Edit and Search

```bash
# Edit title or body
gh issue edit 42 --title "New title"
gh issue edit 42 --body "New body"

# List open issues
gh issue list

# Search with filters
gh issue list --search "label:bug sort:updated-desc"
gh issue list --label "engine" --state open
```

## Issue Types (GraphQL)

Issue types are not exposed via the standard CLI. Use GraphQL mutations.

### Lookup Project Issue Types

```bash
gh api graphql -f query='
  query {
    repository(owner: "xeek-dev", name: "squishmark") {
      issueTypes(first: 10) {
        nodes { id name }
      }
    }
  }
'
```

### Known Issue Type IDs

| Type | ID |
|------|----|
| Task | `IT_kwDOBA-w0M4Aw6D3` |
| Bug | `IT_kwDOBA-w0M4Aw6D4` |
| Feature | `IT_kwDOBA-w0M4Aw6D7` |

### Set Issue Type

```bash
gh api graphql -f query='
  mutation {
    updateIssue(input: {
      id: "ISSUE_NODE_ID",
      issueTypeId: "IT_kwDOBA-w0M4Aw6D3"
    }) {
      issue { title }
    }
  }
'
```

To get the issue node ID: `gh issue view 42 --json id --jq .id`

## Sub-Issues (GraphQL)

Sub-issues use a parent-child relationship. Each issue can have at most one parent.

### Add Sub-Issue

```bash
gh api graphql -f query='
  mutation {
    addSubIssue(input: {
      issueId: "PARENT_NODE_ID",
      subIssueId: "CHILD_NODE_ID"
    }) {
      issue { title }
      subIssue { title }
    }
  }
'
```

## Labels

### Existing Labels

bug, documentation, duplicate, enhancement, good first issue, help wanted, invalid, question, wontfix, engine, themes, content, seo, ai, dx

### Commands

```bash
# Add labels
gh issue edit 42 --add-label "engine,themes"

# Remove labels
gh issue edit 42 --remove-label "duplicate"

# List all labels
gh label list

# Create a new label
gh label create "new-label" --color "0E8A16" --description "Label description"
```

## Milestones

Current milestone: **SquishMark 1.0**

```bash
# List milestones (REST)
gh api repos/{owner}/{repo}/milestones --jq '.[] | "\(.number) \(.title)"'

# Assign milestone to issue
gh issue edit 42 --milestone "SquishMark 1.0"

# Assign milestone to PR
gh pr edit 42 --milestone "SquishMark 1.0"
```

## Pull Requests

### Create

Always use HEREDOC for the body and link to the issue with `Closes #N`:

```bash
gh pr create --title "feat(engine): add dark mode" --body "$(cat <<'EOF'
## Summary
- Add dark mode toggle to settings
- Persist preference across sessions

Closes #42
EOF
)"
```

### Review and Comment

```bash
# View PR details
gh pr view 42

# Check CI status
gh pr checks 42

# Add a comment (always sign with *— Claude*)
gh pr comment 42 --body "$(cat <<'EOF'
Looks good! One minor suggestion on the error handling.

*— Claude*
EOF
)"

# Approve
gh pr review 42 --approve --body "LGTM"
```

### Merge

```bash
# Squash merge (preferred)
gh pr merge 42 --squash

# With custom commit message
gh pr merge 42 --squash --subject "feat(engine): add dark mode (#42)"
```

## Conventions

### Comment Signing

Always sign comments on PRs and issues so it is clear they are AI-generated:

```
Your comment text here.

*— Claude*
```

### Conventional Commits

Commit messages and PR titles must use [Conventional Commits](https://www.conventionalcommits.org/) format:

```
type(scope): description
```

Types: `feat`, `fix`, `refactor`, `chore`, `docs`, `test`, `ci`

### Branch Naming

```
type/issue-description
```

Examples: `feat/42-dark-mode`, `fix/15-header-overflow`, `docs/20-github-skill`

## Auth Troubleshooting

If `gh` commands fail with auth errors:

```bash
gh auth login
gh auth status
```
