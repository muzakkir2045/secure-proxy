from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
import os

router = APIRouter()

AUTH0_DOMAIN  = os.getenv("AUTH0_DOMAIN")
CLIENT_ID     = os.getenv("AUTH0_CLIENT_ID")
BASE_URL      = os.getenv("BASE_URL", "http://localhost:8000")

# Use BASE_URL instead of a separate AUTH0_REDIRECT_URI var
REDIRECT_URI  = f"{BASE_URL}/callback"

PROVIDER_CONNECTION_MAP = {
    "gmail":           "google-oauth2",
    "google-calendar": "google-oauth2",
    "github":          "github",
}

PROVIDER_SCOPES = {
    "gmail": (
        "openid profile email offline_access "
        "https://www.googleapis.com/auth/gmail.readonly"
    ),
    "google-calendar": (
        "openid profile email offline_access "
        "https://www.googleapis.com/auth/calendar"
    ),
    "github": "openid profile email offline_access repo",
}

@router.get("/connect/{provider}")
async def connect_provider(provider: str, request: Request):
    connection = PROVIDER_CONNECTION_MAP.get(provider)
    if not connection:
        return {"error": f"Unknown provider: {provider}"}

    scope = PROVIDER_SCOPES.get(provider, "openid profile email offline_access")

    # Pass provider in state so callback knows what's being connected
    auth_url = (
        f"https://{AUTH0_DOMAIN}/authorize"
        f"?response_type=code"
        f"&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope={scope}"
        f"&connection={connection}"
        f"&access_type=offline"
        f"&prompt=consent"
        f"&state={provider}"           # ← pass provider through state
    )
    return RedirectResponse(auth_url)

# ← /callback is REMOVED from here entirely
#    main.py's /callback handles the code exchange and session storage