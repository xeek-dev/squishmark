---
name: test
description: Run the SquishMark test suite with pytest
disable-model-invocation: true
allowed-tools: Bash(pytest:*)
---

Run the test suite:

```bash
cd D:/xeek-dev/squishmark && pytest $ARGUMENTS
```

Common options:
- `pytest -v` for verbose output
- `pytest -x` to stop on first failure
- `pytest --tb=short` for shorter tracebacks
- `pytest tests/test_specific.py` to run specific test file
