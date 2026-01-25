---
name: format
description: Format the SquishMark codebase with ruff
disable-model-invocation: true
allowed-tools: Bash(ruff:*)
---

Format code with ruff:

```bash
cd D:/xeek-dev/squishmark && ruff format $ARGUMENTS .
```

To check formatting without making changes:

```bash
cd D:/xeek-dev/squishmark && ruff format --check .
```
