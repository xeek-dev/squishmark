"""Authentication routes for GitHub OAuth."""

from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from squishmark.config import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"


@router.get("/login")
async def login(request: Request) -> RedirectResponse:
    """Redirect to GitHub OAuth authorization."""
    settings = get_settings()

    if not settings.github_client_id:
        raise HTTPException(
            status_code=500,
            detail="GitHub OAuth not configured (missing GITHUB_CLIENT_ID)",
        )

    # Build callback URL
    callback_url = str(request.url_for("oauth_callback"))

    # Build authorization URL
    params = {
        "client_id": settings.github_client_id,
        "redirect_uri": callback_url,
        "scope": "read:user",
        "state": settings.secret_key[:16],  # Simple state validation
    }

    auth_url = f"{GITHUB_AUTHORIZE_URL}?{urlencode(params)}"
    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def oauth_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    """Handle GitHub OAuth callback."""
    settings = get_settings()

    # Check for OAuth errors
    if error:
        raise HTTPException(status_code=400, detail=f"OAuth error: {error}")

    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    # Validate state
    if state != settings.secret_key[:16]:
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    # Exchange code for access token
    callback_url = str(request.url_for("oauth_callback"))

    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            GITHUB_TOKEN_URL,
            data={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
                "redirect_uri": callback_url,
            },
            headers={"Accept": "application/json"},
        )

        if token_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get access token")

        token_data = token_response.json()

        if "error" in token_data:
            raise HTTPException(
                status_code=400,
                detail=f"OAuth error: {token_data.get('error_description', token_data['error'])}",
            )

        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(status_code=400, detail="No access token received")

        # Get user info
        user_response = await client.get(
            GITHUB_USER_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
        )

        if user_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get user info")

        user_data = user_response.json()

    # Store user in session
    request.session["user"] = {
        "login": user_data["login"],
        "name": user_data.get("name"),
        "avatar_url": user_data.get("avatar_url"),
    }

    # Redirect to admin
    return RedirectResponse(url="/admin", status_code=302)


@router.get("/logout")
async def logout(request: Request) -> RedirectResponse:
    """Log out the current user."""
    request.session.clear()
    return RedirectResponse(url="/", status_code=302)


@router.get("/me")
async def get_current_user(request: Request) -> dict:
    """Get the current logged-in user."""
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user
