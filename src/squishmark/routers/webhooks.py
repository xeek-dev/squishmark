"""Webhook routes for external integrations."""

import hashlib
import hmac

from fastapi import APIRouter, HTTPException, Request

from squishmark.config import get_settings
from squishmark.services.cache import get_cache
from squishmark.services.github import get_github_service
from squishmark.services.theme import get_theme_engine, reset_theme_engine

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
async def github_webhook(request: Request) -> dict:
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

    # Refresh cache
    cache = get_cache()
    cleared = await cache.clear()

    # Reset theme engine
    reset_theme_engine()

    # Warm the cache
    github_service = get_github_service()

    # Fetch config
    await github_service.get_config(use_cache=True)

    # Fetch all posts
    post_files = await github_service.list_directory("posts", use_cache=True)
    for path in post_files:
        await github_service.get_file(path, use_cache=True)

    # Fetch all pages
    page_files = await github_service.list_directory("pages", use_cache=True)
    for path in page_files:
        await github_service.get_file(path, use_cache=True)

    # Reload theme engine
    await get_theme_engine(github_service)

    return {
        "status": "ok",
        "cleared": cleared,
        "warmed": cache.size,
    }
