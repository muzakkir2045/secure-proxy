import os
from functools import lru_cache
from pydantic import BaseModel


class Settings(BaseModel):
    AUTH0_DOMAIN: str = ""
    AUTH0_CLIENT_ID: str = ""
    AUTH0_CLIENT_SECRET: str = ""
    AUTH0_AUDIENCE: str = ""
    BASE_URL: str = "http://localhost:8000"
    APP_SECRET_KEY: str = "fallback-dev-secret"
    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None

    class Config:
        extra = "allow"


@lru_cache
def get_settings() -> Settings:
    return Settings(
        AUTH0_DOMAIN=os.getenv("AUTH0_DOMAIN", ""),
        AUTH0_CLIENT_ID=os.getenv("AUTH0_CLIENT_ID", ""),
        AUTH0_CLIENT_SECRET=os.getenv("AUTH0_CLIENT_SECRET", ""),
        AUTH0_AUDIENCE=os.getenv("AUTH0_AUDIENCE", ""),
        BASE_URL=os.getenv("BASE_URL", "http://localhost:8000"),
        APP_SECRET_KEY=os.getenv("APP_SECRET_KEY", "fallback-dev-secret"),
        GOOGLE_CLIENT_ID=os.getenv("GOOGLE_CLIENT_ID"),
        GOOGLE_CLIENT_SECRET=os.getenv("GOOGLE_CLIENT_SECRET"),
    )


settings = get_settings()

PROVIDER_SCOPES_LIST = {
    "gmail": ["https://www.googleapis.com/auth/gmail.readonly"],
    "google-calendar": ["https://www.googleapis.com/auth/calendar"],
    "github": ["repo"],
}

PROVIDER_CONNECTION_MAP = {
    "gmail": "google-oauth2",
    "google-calendar": "google-oauth2",
    "github": "github",
}

PROVIDER_SCOPES = {
    "gmail": (
        "openid profile email offline_access "
        "https://www.googleapis.com/auth/gmail.readonly"
    ),
    "google-calendar": (
        "openid profile email offline_access https://www.googleapis.com/auth/calendar"
    ),
    "github": "openid profile email offline_access repo",
}
