---
name: docker
description: Dockerfile standards for Python applications with hatchling
---

# Dockerfile Standards

## Python with Hatchling

When using hatchling as build backend, copy ALL files referenced in pyproject.toml before `pip install .`:

```dockerfile
COPY pyproject.toml README.md ./
COPY src/ src/
RUN pip install --no-cache-dir .
```

Common files needed:
- `pyproject.toml` (always)
- `README.md` (if `readme` field set)
- `LICENSE` (if `license-files` field set)
- Source directory (`src/` or package name)

## Multi-stage Builds

Use multi-stage builds to minimize final image size:

```dockerfile
# Base: install dependencies
FROM python:3.12-slim AS base
COPY pyproject.toml README.md ./
COPY src/ src/
RUN pip install --no-cache-dir .

# Dev: add dev tools, mount source
FROM base AS dev
RUN pip install --no-cache-dir ".[dev]"
COPY . .

# Prod: minimal runtime
FROM base AS prod
COPY themes/ themes/
```

## Best Practices

- Use `python:3.x-slim` not full image
- `--no-cache-dir` with pip to reduce image size
- Clean up apt lists: `rm -rf /var/lib/apt/lists/*`
- Non-root user for production (security)
- `.dockerignore` to exclude `.git`, `__pycache__`, `.venv`, etc.
