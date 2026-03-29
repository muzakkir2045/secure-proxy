from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from app.config import settings, PROVIDER_CONNECTION_MAP, PROVIDER_SCOPES

router = APIRouter()


@router.get("/connect/{provider}")
async def connect_provider(provider: str, request: Request):
    connection = PROVIDER_CONNECTION_MAP.get(provider)
    if not connection:
        return {"error": f"Unknown provider: {provider}"}

    scope = PROVIDER_SCOPES.get(provider, "openid profile email offline_access")

    auth_url = (
        f"https://{settings.AUTH0_DOMAIN}/authorize"
        f"?response_type=code"
        f"&client_id={settings.AUTH0_CLIENT_ID}"
        f"&redirect_uri={settings.BASE_URL}/callback"
        f"&scope={scope}"
        f"&connection={connection}"
        f"&access_type=offline"
        f"&prompt=consent"
        f"&state={provider}"
    )
    return RedirectResponse(auth_url)


@router.get("/connect/all")
async def connect_all(request: Request):
    providers = ["gmail", "google-calendar", "github"]
    connected = []
    not_connected = []

    for provider in providers:
        token = request.session.get("provider_tokens", {}).get(provider)
        if token:
            connected.append(provider)
        else:
            not_connected.append(provider)

    if not_connected:
        return RedirectResponse(f"/connect/{not_connected[0]}")

    return RedirectResponse("/")
