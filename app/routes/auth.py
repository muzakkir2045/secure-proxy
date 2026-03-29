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

    # Get user info
    async with httpx.AsyncClient() as client:
        userinfo_resp = await client.get(
            f"https://{settings.AUTH0_DOMAIN}/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    userinfo = userinfo_resp.json()
    sub = userinfo.get("sub", "")
    print(f"[Callback] sub={sub}, state={state}")

    # Always set login session first
    request.session["access_token"] = access_token
    request.session["user_id"] = sub
    request.session["logged_in"] = True

    # ── Handle provider token based on state (from /connect/x) ───────
    if state == "github":
        provider_tokens = request.session.get("provider_tokens", {})
        provider_tokens["github"] = access_token
        request.session["provider_tokens"] = provider_tokens
        await store_vault_token(sub, "github", access_token, refresh_token)
        print(f"[Callback] ✅ Stored GitHub token via /connect/github")
        return RedirectResponse("/")

    if state in ("gmail", "google-calendar"):
        provider_tokens = request.session.get("provider_tokens", {})
        provider_tokens["gmail"] = access_token
        provider_tokens["google-calendar"] = access_token
        request.session["provider_tokens"] = provider_tokens
        await store_vault_token(sub, "gmail", access_token, refresh_token)
        await store_vault_token(sub, "google-calendar", access_token, refresh_token)
        print(f"[Callback] ✅ Stored Google tokens via /connect/gmail")
        return RedirectResponse("/")

    # ── Auto-detect provider from sub (initial login) ─────────────────
    provider_tokens = request.session.get("provider_tokens", {})

    if "github" in sub:
        # Fetch the actual GitHub token from Auth0 identity
        try:
            mgmt_token = await _get_mgmt_token()
            async with httpx.AsyncClient() as client:
                user_resp = await client.get(
                    f"https://{settings.AUTH0_DOMAIN}/api/v2/users/{sub}",
                    headers={"Authorization": f"Bearer {mgmt_token}"},
                )
            identities = user_resp.json().get("identities", [])
            print(f"[Callback] identities: {identities}")
            for identity in identities:
                if identity.get("provider") == "github":
                    github_token = identity.get("access_token")
                    print(f"[Callback] GitHub token from identity: {github_token[:15] if github_token else 'None'}")
                    if github_token:
                        provider_tokens["github"] = github_token
                        await store_vault_token(sub, "github", github_token, None)
        except Exception as e:
            print(f"[Callback] Failed to fetch GitHub identity token: {e}")
            # Fallback — use the Auth0 access token
            provider_tokens["github"] = access_token

    elif "google-oauth2" in sub:
        provider_tokens["gmail"] = access_token
        provider_tokens["google-calendar"] = access_token
        await store_vault_token(sub, "gmail", access_token, refresh_token)
        await store_vault_token(sub, "google-calendar", access_token, refresh_token)

    request.session["provider_tokens"] = provider_tokens
    print(f"[Callback] provider_tokens keys: {list(provider_tokens.keys())}")
    return RedirectResponse("/")


async def _get_mgmt_token() -> str:
    """Helper to get Auth0 management token."""
    from app.config import settings
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://{settings.AUTH0_DOMAIN}/oauth/token",
            json={
                "grant_type": "client_credentials",
                "client_id": settings.AUTH0_CLIENT_ID,
                "client_secret": settings.AUTH0_CLIENT_SECRET,
                "audience": f"https://{settings.AUTH0_DOMAIN}/api/v2/",
            },
        )
    return resp.json().get("access_token", "")