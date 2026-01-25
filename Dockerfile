# syntax=docker/dockerfile:1

# Base stage with Python and dependencies
FROM python:3.14-slim AS base

WORKDIR /app

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

COPY themes/ themes/

RUN mkdir -p /data

EXPOSE 8000

CMD ["uvicorn", "squishmark.main:app", "--host", "0.0.0.0", "--port", "8000"]
