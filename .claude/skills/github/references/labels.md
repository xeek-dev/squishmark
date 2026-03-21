# Labels

## Existing Labels

bug, documentation, duplicate, enhancement, good first issue, help wanted, invalid, question, wontfix, engine, themes, content, seo, ai, dx

## Commands

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
