from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
import httpx

from app.config import settings
from app.routes import auth, connect, agent


def validate_config():
    missing = [
        k
        for k, v in {
            "AUTH0_DOMAIN": settings.AUTH0_DOMAIN,
            "AUTH0_CLIENT_ID": settings.AUTH0_CLIENT_ID,
            "AUTH0_CLIENT_SECRET": settings.AUTH0_CLIENT_SECRET,
            "AUTH0_AUDIENCE": settings.AUTH0_AUDIENCE,
            "BASE_URL": settings.BASE_URL,
        }.items()
        if not v
    ]
    if missing:
        raise RuntimeError(f"Missing required env vars: {missing}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_config()
    app.state.http_client = httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0))
    yield
    await app.state.http_client.aclose()


app = FastAPI(title="SecureProxy", lifespan=lifespan)

app.include_router(auth.router)
app.include_router(connect.router)
app.include_router(agent.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.APP_SECRET_KEY,
)

app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")


@app.get("/", response_class=HTMLResponse)
async def root():
    with open("frontend/index.html", encoding="utf-8") as f:
        return HTMLResponse(f.read())
