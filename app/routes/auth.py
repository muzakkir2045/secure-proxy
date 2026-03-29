import httpx
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse

from app.config import settings
from app.models.schemas import StatusResponse
from app.services.token_manager import store_vault_token

router = APIRouter()


@router.get("/login")
async def login():
    redirect_uri = f"{settings.BASE_URL}/callback"
    auth_url = (
        f"https://{settings.AUTH0_DOMAIN}/authorize"
        f"?response_type=code"
        f"&client_id={settings.AUTH0_CLIENT_ID}"
        f"&redirect_uri={redirect_uri}"
        f"&scope=openid profile email offline_access"
        f"&audience={settings.AUTH0_AUDIENCE}"
    )
    return RedirectResponse(auth_url)


@router.get("/callback")
async def callback(request: Request, code: str = None, state: str = None):
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://{settings.AUTH0_DOMAIN}/oauth/token",
            json={
                "grant_type": "authorization_code",
                "client_id": settings.AUTH0_CLIENT_ID,
                "client_secret": settings.AUTH0_CLIENT_SECRET,
                "code": code,
                "redirect_uri": f"{settings.BASE_URL}/callback",
            },
        )
    token_data = resp.json()
    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")

    if not access_token:
        raise HTTPException(
            status_code=400, detail=f"Token exchange failed: {token_data}"
        )

    async with httpx.AsyncClient() as client:
        userinfo_resp = await client.get(
            f"https://{settings.AUTH0_DOMAIN}/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    userinfo = userinfo_resp.json()
    sub = userinfo.get("sub", "")

    if sub.startswith("google-oauth2"):
        provider_tokens = request.session.get("provider_tokens", {})
        provider_tokens["gmail"] = access_token
        provider_tokens["google-calendar"] = access_token
        request.session["provider_tokens"] = provider_tokens

        await store_vault_token(sub, "gmail", access_token, refresh_token)
        await store_vault_token(sub, "google-calendar", access_token, refresh_token)

    elif sub.startswith("github"):
        provider_tokens = request.session.get("provider_tokens", {})
        provider_tokens["github"] = access_token
        request.session["provider_tokens"] = provider_tokens

        await store_vault_token(sub, "github", access_token, refresh_token)

    if not request.session.get("logged_in"):
        request.session["access_token"] = access_token
        request.session["user_id"] = sub
        request.session["logged_in"] = True

    return RedirectResponse("/")


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/")


@router.get("/status", response_model=StatusResponse)
async def status(request: Request):
    return StatusResponse(
        logged_in=request.session.get("logged_in", False),
        user_id=request.session.get("user_id"),
        providers_linked=list(request.session.get("provider_tokens", {}).keys()),
        message="SecureProxy is running",
    )
