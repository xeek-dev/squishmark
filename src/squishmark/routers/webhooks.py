"""Webhook routes for external integrations."""

import hashlib
import hmac
import json
import string

from fastapi import APIRouter, HTTPException, Request

from squishmark.config import get_settings
from squishmark.dependencies import ServicesDep, ThemeEngineDep
from squishmark.services.content import warm_content_caches
from squishmark.services.search import warm_search_indexes

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def verify_github_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify GitHub webhook signature."""
    if not signature.startswith("sha256="):
        return False

    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(f"sha256={expected}", signature)


@router.post("/github")
async def github_webhook(request: Request, services: ServicesDep, theme_engine: ThemeEngineDep) -> dict:
    """
    Handle GitHub webhook for automatic cache refresh.

    This endpoint is called by GitHub when content is pushed to the
    content repository. It verifies the webhook signature and refreshes
    the cache.
    """
    settings = get_settings()

    # Verify webhook secret is configured
    if not settings.github_webhook_secret:
        raise HTTPException(
            status_code=500,
            detail="Webhook secret not configured",
        )

    # Get signature from header
    signature = request.headers.get("X-Hub-Signature-256", "")
    if not signature:
        raise HTTPException(status_code=401, detail="Missing signature")

    # Get raw body for signature verification
    body = await request.body()

    # Verify signature
    if not verify_github_signature(body, signature, settings.github_webhook_secret):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Get event type
    event = request.headers.get("X-GitHub-Event", "")

    # Only process push events
    if event != "push":
        return {"status": "ignored", "event": event}

    # Pin content fetches to the pushed commit. Fetching by SHA sidesteps
    # the raw CDN's branch-path caching, which can otherwise serve the
    # pre-push file for minutes and poison the warm below (issue #138).
    github_service = services.github
    pinned_ref = None
    try:
        payload = json.loads(body)
    except ValueError, UnicodeDecodeError:
        payload = {}
    after = payload.get("after", "")
    branch = payload.get("ref", "")
    is_sha = len(after) == 40 and set(after) <= set(string.hexdigits.lower()) and set(after) != {"0"}
    if branch == f"refs/heads/{github_service.DEFAULT_BRANCH}" and is_sha:
        github_service.pin_content_ref(after)
        pinned_ref = after

    # Refresh cache
    cache = services.cache
    cleared = await cache.clear()

    # Reload theme engine templates and favicon detection
    await theme_engine.reload()

    # Warm the cache
    github_service = services.github

    # Fetch config
    await github_service.get_config(use_cache=True)

    # Fetch all posts
    post_files = await github_service.list_directory("posts", use_cache=True)
    for path in post_files:
        await github_service.get_file(path, use_cache=True)

    # Fetch all pages
    page_files = await github_service.list_directory("pages", use_cache=True, recursive=True)
    for path in page_files:
        await github_service.get_file(path, use_cache=True)

    # Pre-parse posts and pages so the first render after a push isn't cold
    await warm_content_caches(services)

    # Pre-build both search index variants so the first search isn't cold
    await warm_search_indexes(services)

    return {
        "status": "ok",
        "cleared": cleared,
        "warmed": cache.size,
        "content_ref": pinned_ref or github_service.DEFAULT_BRANCH,
    }
