"""Search route."""

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from squishmark.dependencies import is_admin
from squishmark.services.search import (
    DEFAULT_LIMIT,
    MIN_QUERY_LENGTH,
    get_search_index,
    query_index,
)

router = APIRouter(tags=["search"])


@router.get("/search")
async def search(request: Request, q: str = Query("", max_length=200)) -> JSONResponse:
    """Search posts by keyword; admins also match drafts.

    Short or empty queries return an empty result set with 200 (the client
    fires on every debounce tick — an error status would just be noise).
    The response is never cacheable: it varies by session (drafts).
    """
    query = q.strip()
    results: list[dict] = []

    if len(query) >= MIN_QUERY_LENGTH:
        index = await get_search_index(include_drafts=is_admin(request))
        results = [r.model_dump(mode="json") for r in query_index(query, index, limit=DEFAULT_LIMIT)]

    return JSONResponse(
        content={"query": query, "results": results},
        headers={"Cache-Control": "no-store"},
    )
