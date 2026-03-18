from fastapi import FastAPI, Request, HTTPException 
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse 
from fastapi.staticfiles import StaticFiles 
from fastapi.middleware.cors import CORSMiddleware 
from starlette.middleware.sessions import SessionMiddleware 
from dotenv import load_dotenv 
import os, httpx 
 
load_dotenv() 
 
app = FastAPI(title='SecureProxy') 
 
# Allow frontend to talk to backend 
app.add_middleware(CORSMiddleware, 
    allow_origins=['*'], allow_methods=['*'], allow_headers=['*']) 
 
# Session needed to store user login state 
app.add_middleware(SessionMiddleware, 
    secret_key=os.getenv('APP_SECRET_KEY')) 
 
# Serve frontend files 
app.mount('/frontend', StaticFiles(directory='frontend'), name='frontend') 
 
AUTH0_DOMAIN = os.getenv('AUTH0_DOMAIN') 
CLIENT_ID    = os.getenv('AUTH0_CLIENT_ID') 
CLIENT_SECRET = os.getenv('AUTH0_CLIENT_SECRET') 
AUDIENCE     = os.getenv('AUTH0_AUDIENCE') 
BASE_URL     = os.getenv('BASE_URL') 
 
 
@app.get('/', response_class=HTMLResponse) 
async def root(): 
    with open('frontend/index.html') as f: 
        return HTMLResponse(f.read()) 


# ── Auth0 login ────────────────────────────────────────────────── 
@app.get('/login') 
async def login(request: Request): 
    redirect_uri = f'{BASE_URL}/callback' 
    auth_url = ( 
        f'https://{AUTH0_DOMAIN}/authorize' 
        f'?response_type=code' 
        f'&client_id={CLIENT_ID}' 
        f'&redirect_uri={redirect_uri}' 
        f'&scope=openid profile email' 
        f'&audience={AUDIENCE}' 
    ) 
    return RedirectResponse(auth_url) 

@app.get('/callback') 
async def callback(request: Request, code: str): 
    # Exchange auth code for tokens 
    async with httpx.AsyncClient() as client: 
        resp = await client.post( 
        f'https://{AUTH0_DOMAIN}/oauth/token', 
        json={ 
            'grant_type': 'authorization_code', 
            'client_id': CLIENT_ID, 
            'client_secret': CLIENT_SECRET, 
            'code': code, 
            'redirect_uri': f'{BASE_URL}/callback' 
            } 
        ) 
    token_data = resp.json() 
    request.session['access_token'] = token_data.get('access_token') 
    request.session['logged_in'] = True 
    return RedirectResponse('/') 


@app.get('/logout') 
async def logout(request: Request): 
    request.session.clear() 
    return RedirectResponse('/') 


# ── Agent task endpoint ─────────────────────────────────────────── 
@app.post('/agent/task') 
async def agent_task(request: Request, body: dict): 
    """ 
    OpenClaw sends POST /agent/task with a JSON body like: 
    { "action": "fetch_emails", "params": { "count": 5 } } 
    """ 
    if not request.session.get('logged_in'): 
        raise HTTPException(status_code=401, detail='Not authenticated') 
    action = body.get('action') 
    if action == 'fetch_emails': 
        from api_clients import fetch_emails 
        token = await get_vault_token(request, 'gmail') 
        return await fetch_emails(token, body.get('params', {})) 
    elif action == 'create_calendar_event': 
        from api_clients import create_calendar_event 
        token = await get_vault_token(request, 'google_calendar') 
        return await create_calendar_event(token, body.get('params', {})) 
 
    elif action == 'create_github_issue': 
        from api_clients import create_github_issue 
        token = await get_vault_token(request, 'github') 
        return await create_github_issue(token, body.get('params', {})) 
 
    else: 
        raise HTTPException(status_code=400, detail=f'Unknown action: {action}') 
 
 
async def get_vault_token(request: Request, provider: str) -> str: 
    """ 
    Calls Auth0 Token Vault to retrieve a stored OAuth token 
    for a given provider (gmail, google_calendar, github). 
    """ 
    user_token = request.session.get('access_token') 
    async with httpx.AsyncClient() as client: 
        resp = await client.get( 
            f'https://{AUTH0_DOMAIN}/api/v2/token-vault/tokens/{provider}', 
            headers={'Authorization': f'Bearer {user_token}'} 
        ) 
    if resp.status_code != 200: 
        raise HTTPException( 
            status_code=403, 
            detail=f'No vault token for {provider}. User must connect this account first.' 
        ) 
    return resp.json()['access_token'] 
 
 
# ── Status endpoint ─────────────────────────────────────────────── 
@app.get('/status') 
async def status(request: Request): 
    return { 
        'logged_in': request.session.get('logged_in', False), 
        'message': 'SecureProxy is running' 
    }
