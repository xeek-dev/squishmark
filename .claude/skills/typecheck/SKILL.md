---
name: typecheck
description: Run pyright type checking on the SquishMark codebase
disable-model-invocation: true
allowed-tools: Bash(pyright:*)
---

Run type checking with pyright:

```bash
cd D:/xeek-dev/squishmark && pyright $ARGUMENTS
```

Pyright is configured in `pyproject.toml` with standard type checking mode.
