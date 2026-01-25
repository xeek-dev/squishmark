# syntax=docker/dockerfile:1

# Base stage with Python and dependencies
FROM python:3.12-slim AS base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Copy project files needed for installation
COPY pyproject.toml README.md ./
COPY src/ src/

# Install production dependencies
RUN pip install --no-cache-dir .

# Development stage - includes dev dependencies
FROM base AS dev

RUN pip install --no-cache-dir ".[dev]"

COPY . .

EXPOSE 8000

CMD ["uvicorn", "squishmark.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production stage - minimal image
FROM base AS prod

# Copy application code
COPY src/ src/
COPY themes/ themes/

# Create data directory for SQLite
RUN mkdir -p /data

EXPOSE 8000

CMD ["uvicorn", "squishmark.main:app", "--host", "0.0.0.0", "--port", "8000"]
