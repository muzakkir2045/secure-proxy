from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from auth import router as auth_router
from dotenv import load_dotenv
from contextlib import asynccontextmanager
import os, httpx

load_dotenv()

AUTH0_DOMAIN  = os.getenv('AUTH0_DOMAIN')
CLIENT_ID     = os.getenv('AUTH0_CLIENT_ID')
CLIENT_SECRET = os.getenv('AUTH0_CLIENT_SECRET')
AUDIENCE      = os.getenv('AUTH0_AUDIENCE')
BASE_URL      = os.getenv('BASE_URL', 'http://localhost:8000')

PROVIDER_SCOPES_LIST = {
    'gmail':           ['https://www.googleapis.com/auth/gmail.readonly'],
    'google-calendar': ['https://www.googleapis.com/auth/calendar'],
    'github':          ['repo'],
}


# ── Startup validation ──────────────────────────────────────────────
def validate_config():
    missing = [k for k, v in {
        'AUTH0_DOMAIN':        AUTH0_DOMAIN,
        'AUTH0_CLIENT_ID':     CLIENT_ID,
        'AUTH0_CLIENT_SECRET': CLIENT_SECRET,
        'AUTH0_AUDIENCE':      AUDIENCE,
        'BASE_URL':            BASE_URL,
    }.items() if not v]
    if missing:
        raise RuntimeError(f"Missing required env vars: {missing}")


# ── Lifespan (startup/shutdown) ─────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_config()
    app.state.http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(10.0, connect=5.0)
    )
    yield
    await app.state.http_client.aclose()


# ── App setup ───────────────────────────────────────────────────────
app = FastAPI(title='SecureProxy', lifespan=lifespan)

app.include_router(auth_router)

app.add_middleware(CORSMiddleware,
    allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])

app.add_middleware(SessionMiddleware,
    secret_key=os.getenv('APP_SECRET_KEY', 'fallback-dev-secret'))

app.mount('/frontend', StaticFiles(directory='frontend'), name='frontend')


# ── Routes ──────────────────────────────────────────────────────────
@app.get('/', response_class=HTMLResponse)
async def root():
    with open('frontend/index.html', encoding='utf-8') as f:
        return HTMLResponse(f.read())


@app.get('/login')
async def login(request: Request):
    redirect_uri = f'{BASE_URL}/callback'
    auth_url = (
        f'https://{AUTH0_DOMAIN}/authorize'
        f'?response_type=code'
        f'&client_id={CLIENT_ID}'
        f'&redirect_uri={redirect_uri}'
        f'&scope=openid profile email offline_access'
        f'&audience={AUDIENCE}'
    )
    return RedirectResponse(auth_url)


@app.get('/callback')
async def callback(request: Request, code: str = None, state: str = None):
    if not code:
        raise HTTPException(status_code=400, detail='Missing authorization code')

    # 1. Exchange code for tokens
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f'https://{AUTH0_DOMAIN}/oauth/token',
            json={
                'grant_type':    'authorization_code',
                'client_id':     CLIENT_ID,
                'client_secret': CLIENT_SECRET,
                'code':          code,
                'redirect_uri':  f'{BASE_URL}/callback'
            }
        )
    token_data = resp.json()
    access_token  = token_data.get('access_token')
    refresh_token = token_data.get('refresh_token')

    if not access_token:
        raise HTTPException(status_code=400, detail=f'Token exchange failed: {token_data}')

    # 2. Get user info
    async with httpx.AsyncClient() as client:
        userinfo_resp = await client.get(
            f'https://{AUTH0_DOMAIN}/userinfo',
            headers={'Authorization': f'Bearer {access_token}'}
        )
    userinfo = userinfo_resp.json()
    sub = userinfo.get('sub', '')  # e.g. "google-oauth2|123456"

    # 3. Store provider token in session (fallback) + attempt Token Vault storage
    if sub.startswith('google-oauth2'):
        provider_tokens = request.session.get('provider_tokens', {})
        provider_tokens['gmail']           = access_token
        provider_tokens['google-calendar'] = access_token
        request.session['provider_tokens'] = provider_tokens

        # Attempt to store in Token Vault
        await store_vault_token(sub, 'gmail',           access_token, refresh_token)
        await store_vault_token(sub, 'google-calendar', access_token, refresh_token)

    elif sub.startswith('github'):
        provider_tokens = request.session.get('provider_tokens', {})
        provider_tokens['github']          = access_token
        request.session['provider_tokens'] = provider_tokens

        # Attempt to store in Token Vault
        await store_vault_token(sub, 'github', access_token, refresh_token)

    # 4. Set session on first login only
    if not request.session.get('logged_in'):
        request.session['access_token'] = access_token
        request.session['user_id']      = sub
        request.session['logged_in']    = True

    return RedirectResponse('/')


@app.get('/logout')
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse('/')


# ── Token Vault helpers ─────────────────────────────────────────────
async def get_management_token() -> str:
    """Get a Management API token using client credentials."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f'https://{AUTH0_DOMAIN}/oauth/token',
            json={
                'grant_type':    'client_credentials',
                'client_id':     CLIENT_ID,
                'client_secret': CLIENT_SECRET,
                'audience':      f'https://{AUTH0_DOMAIN}/api/v2/'
            }
        )
    data = resp.json()
    token = data.get('access_token')
    if not token:
        raise HTTPException(status_code=500, detail=f'Failed to get mgmt token: {data}')
    return token


async def store_vault_token(
    user_id: str,
    provider: str,
    access_token: str,
    refresh_token: str = None
):
    """
    Store a provider OAuth token into Auth0 Token Vault.
    Silently logs on failure so it doesn't break the login flow.
    """
    try:
        mgmt_token = await get_management_token()
        body = {
            'name':         provider,
            'access_token': access_token,
            'provider':     'google-oauth2' if 'google' in provider else provider,
            'scopes':       PROVIDER_SCOPES_LIST.get(provider, [])
        }
        if refresh_token:
            body['refresh_token'] = refresh_token

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f'https://{AUTH0_DOMAIN}/api/v2/users/{user_id}/tokens',
                headers={'Authorization': f'Bearer {mgmt_token}'},
                json=body
            )
        print(f"[Token Vault] STORE {provider} → {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"[Token Vault] STORE failed for {provider}: {e}")


async def get_google_token_from_auth0(user_id: str, mgmt_token: str) -> str:
    """
    Fetches the raw Google OAuth token Auth0 is holding internally.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f'https://{AUTH0_DOMAIN}/api/v2/users/{user_id}',
            headers={'Authorization': f'Bearer {mgmt_token}'}
        )
    
    user_data = resp.json()
    print(f"[DEBUG] Full user data: {user_data}")  # see what Auth0 has

    # Auth0 stores provider identities here
    identities = user_data.get('identities', [])
    for identity in identities:
        if identity.get('provider') == 'google-oauth2':
            google_token = identity.get('access_token')
            print(f"[DEBUG] Found Google token: {str(google_token)[:50]}")
            return google_token

    return None


async def refresh_google_token(user_id: str) -> str:
    """Uses Auth0 to get a fresh Google token via refresh token."""
    try:
        mgmt_token = await get_management_token()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f'https://{AUTH0_DOMAIN}/api/v2/users/{user_id}',
                headers={'Authorization': f'Bearer {mgmt_token}'}
            )
        identities = resp.json().get('identities', [])
        for identity in identities:
            if identity.get('provider') == 'google-oauth2':
                refresh_token = identity.get('refresh_token')
                if not refresh_token:
                    raise Exception("No refresh token stored")

                # Exchange refresh token for new access token
                async with httpx.AsyncClient() as client:
                    token_resp = await client.post(
                        'https://oauth2.googleapis.com/token',
                        data={
                            'client_id':     os.getenv('GOOGLE_CLIENT_ID'),
                            'client_secret': os.getenv('GOOGLE_CLIENT_SECRET'),
                            'refresh_token': refresh_token,
                            'grant_type':    'refresh_token'
                        }
                    )
                new_token = token_resp.json().get('access_token')
                print(f"[Token] ✅ Refreshed Google token")
                return new_token
    except Exception as e:
        print(f"[Token] Refresh failed: {e}")
        return None


@app.get('/reconnect/{provider}')
async def reconnect(provider: str):
    """Auto-reconnects a provider when token expires."""
    return RedirectResponse(f'/connect/{provider}')

async def get_vault_token(request: Request, provider: str) -> str:
    user_id    = request.session.get('user_id')
    user_token = request.session.get('access_token')

    if not user_token:
        raise HTTPException(status_code=401, detail='Not authenticated')

    # ── Fetch raw provider token from Auth0 identities ──────────────
    if user_id:
        try:
            mgmt_token = await get_management_token()
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f'https://{AUTH0_DOMAIN}/api/v2/users/{user_id}',
                    headers={'Authorization': f'Bearer {mgmt_token}'}
                )
            user_data  = resp.json()
            identities = user_data.get('identities', [])

            # Map provider name to Auth0 identity provider string
            provider_map = {
                'gmail':           'google-oauth2',
                'google-calendar': 'google-oauth2',
                'github':          'github',
            }
            target = provider_map.get(provider)



            for identity in identities:
                if identity.get('provider') == target:
                    raw_token = identity.get('access_token')
                    # After getting raw_token from identities, verify it's still valid
                    if raw_token:
                        # Quick validation check against Google tokeninfo
                        async with httpx.AsyncClient() as client:
                            check = await client.get(
                                f'https://oauth2.googleapis.com/tokeninfo?access_token={raw_token}'
                            )
                        if check.status_code != 200:
                            print(f"[Token] Token expired, attempting refresh...")
                            if provider in ('gmail', 'google-calendar'):
                                refreshed = await refresh_google_token(user_id)
                                if refreshed:
                                    return refreshed
                            raise HTTPException(
                                status_code=403,
                                detail=f'Token expired for {provider}. Visit /connect/{provider} to reconnect.'
                            )
        except Exception as e:
            print(f"[Token] Identity fetch failed for {provider}: {e}")

    # ── Fallback to session ─────────────────────────────────────────
    session_token = request.session.get('provider_tokens', {}).get(provider)
    if session_token:
        print(f"[Token] ⚠️ Using session fallback for {provider}")
        return session_token

    raise HTTPException(
        status_code=403,
        detail=f'No token for {provider}. Visit /connect/{provider} first.'
    )

# ── Agent task endpoint ─────────────────────────────────────────────
from pydantic import BaseModel

class AgentTaskRequest(BaseModel):
    action: str
    params: dict = {}

@app.post('/agent/task')
async def agent_task(request: Request, body: AgentTaskRequest):
    if not request.session.get('logged_in'):
        raise HTTPException(status_code=401, detail='Not authenticated')

    action = body.action
    params = body.params

    # ← Unwrap if frontend is double-nesting the body
    if 'action' in params and 'params' in params:
        print("[AgentTask] Detected double-nested body, unwrapping...")
        action = params.get('action', action)
        params = params.get('params', {})

    print(f"[AgentTask] action={action}, params={params}")

    if action == 'fetch_emails':
        from api_clients import fetch_emails
        token = await get_vault_token(request, 'gmail')
        return await fetch_emails(token, params)

    elif action == 'create_calendar_event':
        from api_clients import create_calendar_event
        token = await get_vault_token(request, 'google-calendar')
        return await create_calendar_event(token, params)

    elif action == 'create_github_issue':
        from api_clients import create_github_issue
        token = await get_vault_token(request, 'github')
        return await create_github_issue(token, params)

    else:
        raise HTTPException(status_code=400, detail=f'Unknown action: {action}')


# ── Status endpoint ─────────────────────────────────────────────────
@app.get('/status')
async def status(request: Request):
    return {
        'logged_in':       request.session.get('logged_in', False),
        'user_id':         request.session.get('user_id'),
        'providers_linked': list(request.session.get('provider_tokens', {}).keys()),
        'message':         'SecureProxy is running'
    }