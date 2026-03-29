import httpx
from fastapi import HTTPException, Request

from app.config import settings, PROVIDER_SCOPES_LIST


async def get_management_token() -> str:
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
    data = resp.json()
    token = data.get("access_token")
    if not token:
        raise HTTPException(status_code=500, detail=f"Failed to get mgmt token: {data}")
    return token


async def store_vault_token(
    user_id: str,
    provider: str,
    access_token: str,
    refresh_token: str | None = None,
) -> None:
    try:
        mgmt_token = await get_management_token()
        body = {
            "name": provider,
            "access_token": access_token,
            "provider": "google-oauth2" if "google" in provider else provider,
            "scopes": PROVIDER_SCOPES_LIST.get(provider, []),
        }
        if refresh_token:
            body["refresh_token"] = refresh_token

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://{settings.AUTH0_DOMAIN}/api/v2/users/{user_id}/tokens",
                headers={"Authorization": f"Bearer {mgmt_token}"},
                json=body,
            )
        print(f"[Token Vault] STORE {provider} → {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"[Token Vault] STORE failed for {provider}: {e}")


async def refresh_google_token(user_id: str) -> str | None:
    try:
        mgmt_token = await get_management_token()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://{settings.AUTH0_DOMAIN}/api/v2/users/{user_id}",
                headers={"Authorization": f"Bearer {mgmt_token}"},
            )
        identities = resp.json().get("identities", [])
        for identity in identities:
            if identity.get("provider") == "google-oauth2":
                refresh_token = identity.get("refresh_token")
                if not refresh_token:
                    raise Exception("No refresh token stored")

                async with httpx.AsyncClient() as client:
                    token_resp = await client.post(
                        "https://oauth2.googleapis.com/token",
                        data={
                            "client_id": settings.GOOGLE_CLIENT_ID,
                            "client_secret": settings.GOOGLE_CLIENT_SECRET,
                            "refresh_token": refresh_token,
                            "grant_type": "refresh_token",
                        },
                    )
                new_token = token_resp.json().get("access_token")
                print(f"[Token] ✅ Refreshed Google token")
                return new_token
    except Exception as e:
        print(f"[Token] Refresh failed: {e}")
        return None


async def get_vault_token(request: Request, provider: str) -> str:
    user_id = request.session.get("user_id")
    user_token = request.session.get("access_token")

    if not user_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # ── Try Auth0 identity token ──────────────────────────────────────
    if user_id:
        try:
            mgmt_token = await get_management_token()
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"https://{settings.AUTH0_DOMAIN}/api/v2/users/{user_id}",
                    headers={"Authorization": f"Bearer {mgmt_token}"},
                )
            
            if resp.status_code != 200:
                print(f"[Token] Management API failed: {resp.status_code} {resp.text}")
            else:
                user_data = resp.json()
                identities = user_data.get("identities", [])
                provider_map = {
                    "gmail": "google-oauth2",
                    "google-calendar": "google-oauth2",
                    "github": "github",
                }
                target = provider_map.get(provider)

                for identity in identities:
                    if identity.get("provider") == target:
                        raw_token = identity.get("access_token")
                        print(f"[Token] Found {target} token, validating...")

                    
                        print(f"[Token DEBUG] provider={target}")
                        print(f"[Token DEBUG] token prefix={raw_token[:20] if raw_token else 'None'}")

                        if not raw_token:
                            print(f"[Token] No access_token in identity for {target}")
                            break

                        # Validate token (Google only)
                        if target == "google-oauth2":
                            async with httpx.AsyncClient() as client:
                                check = await client.get(
                                    f"https://oauth2.googleapis.com/tokeninfo"
                                    f"?access_token={raw_token}"
                                )
                            
                            if check.status_code == 200:
                                print(f"[Token] ✅ Valid Google token from vault")
                                return raw_token
                            else:
                                print(f"[Token] Token expired, trying refresh...")
                                refreshed = await refresh_google_token(user_id)
                                if refreshed:
                                    # Update session with new token
                                    provider_tokens = request.session.get("provider_tokens", {})
                                    provider_tokens[provider] = refreshed
                                    request.session["provider_tokens"] = provider_tokens
                                    return refreshed
                                else:
                                    print(f"[Token] Refresh failed, falling back to session")
                                    break
                        else:
                            # GitHub tokens don't expire, return directly
                            print(f"[Token] ✅ Valid GitHub token from vault")
                            return raw_token

        except Exception as e:
            print(f"[Token] Vault lookup failed for {provider}: {e}")

    # ── Session fallback ──────────────────────────────────────────────
    session_token = request.session.get("provider_tokens", {}).get(provider)
    if session_token:
        print(f"[Token] ⚠️ Using session fallback for {provider}")
        return session_token

    raise HTTPException(
        status_code=403,
        detail=f"No token for {provider}. Visit /connect/{provider} to reconnect.",
    )