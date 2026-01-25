---
name: lint
description: Run ruff linting on the SquishMark codebase
disable-model-invocation: true
allowed-tools: Bash(ruff:*)
---

Run linting with ruff:

```bash
cd D:/xeek-dev/squishmark && ruff check $ARGUMENTS .
```

To automatically fix issues:

```bash
cd D:/xeek-dev/squishmark && ruff check --fix .
```
