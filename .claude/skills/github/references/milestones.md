# Milestones

Current milestone: **SquishMark 1.0**

```bash
# List milestones (REST)
gh api repos/{owner}/{repo}/milestones --jq '.[] | "\(.number) \(.title)"'

# Assign milestone to issue
gh issue edit 42 --milestone "SquishMark 1.0"

# Assign milestone to PR
gh pr edit 42 --milestone "SquishMark 1.0"
```
