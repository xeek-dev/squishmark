# Pull Requests

## Create

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

## Review and Comment

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

## Merge

```bash
# Squash merge (preferred)
gh pr merge 42 --squash

# With custom commit message
gh pr merge 42 --squash --subject "feat(engine): add dark mode (#42)"
```
