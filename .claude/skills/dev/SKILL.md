---
name: dev
description: Start the SquishMark development server with hot reload
disable-model-invocation: true
allowed-tools: Bash(uvicorn:*)
---

Start the development server:

```bash
cd D:/xeek-dev/squishmark && uvicorn squishmark.main:app --reload --host 0.0.0.0 --port 8000
```

The server will be available at http://localhost:8000 with automatic reload on file changes.
