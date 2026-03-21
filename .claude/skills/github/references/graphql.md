# GitHub GraphQL Operations

## Issue Types

Issue types are not exposed via the standard CLI. Use GraphQL mutations.

**Shortcut:** Use `python .claude/skills/github/scripts/github-issue-updater.py <issue> --type task|bug|feature` to set type, labels, and milestone in one command.

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

## Sub-Issues

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
