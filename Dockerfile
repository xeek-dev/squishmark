# syntax=docker/dockerfile:1

FROM python:3.14-slim AS base

WORKDIR /app

# Install uv for faster package installation
RUN pip install --no-cache-dir uv==0.9.26

# Copy only dependency metadata first (cached unless pyproject.toml changes)
COPY pyproject.toml README.md ./

# Create stub package structure so editable install works
RUN mkdir -p src/squishmark && touch src/squishmark/__init__.py

# Install production dependencies only (this layer is cached)
# Cache mount persists uv's download cache between builds
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system .

# Now copy actual source code (changes frequently, but deps are cached)
COPY src/ src/

# Development stage - includes test dependencies (NOT lint tools)
FROM base AS dev

# Create data directory for SQLite database
RUN mkdir -p /data

# Install test dependencies only - ruff/pyright run locally, not in container
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system ".[test]"

COPY . .

EXPOSE 8000

CMD ["uvicorn", "squishmark.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production stage - minimal image
FROM base AS prod

COPY themes/ themes/

RUN mkdir -p /data

EXPOSE 8000

CMD ["uvicorn", "squishmark.main:app", "--host", "0.0.0.0", "--port", "8000"]
