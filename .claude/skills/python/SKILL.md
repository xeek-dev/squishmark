---
name: python
description: Python coding standards for SquishMark (FastAPI, SQLAlchemy, async)
---

# Python Coding Standards

## FastAPI

- Use `Depends()` for dependency injection
- Return Pydantic models or use `response_model` for type safety
- Use `HTTPException` for error responses with appropriate status codes
- Background tasks for non-blocking operations (analytics, logging)

## SQLAlchemy Async

- Use `AsyncSession` with `aiosqlite` for async database access
- Boolean comparisons: `.is_(True)` not `== True`
- After mutations: `await session.flush()` then `await session.refresh(obj)`
- Fetch-then-delete pattern for async deletes (`.rowcount` unreliable on async Result)
- Use `select()` with `scalars()` for queries:
  ```python
  result = await session.execute(select(Model).where(...))
  items = list(result.scalars().all())
  ```

## Pydantic

- Use `Field()` for defaults and validation
- Union syntax: `str | None` not `Optional[str]`
- Use `model_validator` for cross-field validation
- `pydantic-settings` for environment config with `.env` support

## python-markdown

- `output_format`: Use `"html"` not `"html5"`
- TocExtension with `permalink=True` adds `id` attributes to headings
- Reset markdown instance between renders: `md.reset()`

## General

- Type hints throughout, use `datetime.date` if you have a field named `date`
- Async functions for I/O operations
- Global service instances with getter functions for dependency injection
