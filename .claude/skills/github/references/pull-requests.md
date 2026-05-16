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

## Copilot Code Review

The Copilot reviewer is a GitHub App, **not** a workflow run or check — `gh run list` and `gh pr checks` won't show it. The signals live on the issue/PR timeline and reviews APIs.

### Request

```bash
echo '{"reviewers": ["copilot-pull-request-reviewer[bot]"]}' \
  | gh api repos/{owner}/{repo}/pulls/<num>/requested_reviewers -X POST --input -
```

The brackets in the login matter. `gh pr edit --add-reviewer copilot-pull-request-reviewer` returns 422; `reviewers: ["Copilot"]` is silently dropped.

### Wait

Two signals, in order:

1. **`copilot_work_started`** — timeline event posted within seconds of the request, performed by app `copilot-pull-request-reviewer`. Confirms the bot picked up the request.
   ```bash
   gh api repos/{owner}/{repo}/issues/<num>/timeline --paginate \
     --jq '.[] | select(.event=="copilot_work_started") | .created_at'
   ```
2. **Review submitted** — appears in `pulls/<num>/reviews` (typically <2 min later). After the review lands, allow ~60s before fetching inline comments — they lag the review.
   ```bash
   gh api repos/{owner}/{repo}/pulls/<num>/reviews \
     --jq '.[] | select(.user.login=="copilot-pull-request-reviewer[bot]")'
   gh api repos/{owner}/{repo}/pulls/<num>/comments \
     --jq '.[] | {id, path, line, body}'
   ```

### Reply to inline comments

```bash
gh api repos/{owner}/{repo}/pulls/<num>/comments/<comment_id>/replies \
  -X POST -f body="...
*— Claude*"
```

### Re-review

The bot reviews once per request. New commits don't auto-trigger a re-review — re-request the reviewer for a fresh pass.

### Resolve threads before merging

`main` requires conversation resolution. Replying to a Copilot thread does **not** mark it resolved — that's a separate action. Without resolving, `gh pr merge` fails with `mergeStateStatus: BLOCKED` even with all checks green and no required approvals.

```bash
gh api graphql -f query='{repository(owner:"xeek-dev",name:"squishmark"){pullRequest(number:<num>){reviewThreads(first:50){nodes{id isResolved}}}}}' \
  --jq '.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved==false) | .id' \
| while read -r ID; do
    gh api graphql -f query='mutation($id:ID!){resolveReviewThread(input:{threadId:$id}){thread{isResolved}}}' -f id="$ID"
  done
```

## Merge

```bash
# Squash merge (preferred)
gh pr merge 42 --squash

# With custom commit message
gh pr merge 42 --squash --subject "feat(engine): add dark mode (#42)"
```
