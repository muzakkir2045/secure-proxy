import asyncio
import httpx
from contextlib import asynccontextmanager
from typing import AsyncGenerator

# ── Shared client ────────────────────────────────────────────────────────────
# Reuse a single AsyncClient across all requests (connection pooling).
# In FastAPI, create this once at startup via lifespan and inject it.

DEFAULT_TIMEOUT = httpx.Timeout(10.0, connect=5.0)

@asynccontextmanager
async def get_http_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Yields a shared AsyncClient. Replace with a app-lifespan singleton in prod."""
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        yield client


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Gmail ─────────────────────────────────────────────────────────────────────

async def fetch_emails(access_token: str, params: dict) -> dict:
    count = params.get("count", 5)

    async with get_http_client() as client:
        # 1. Fetch message list
        list_resp = await client.get(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages",
            headers=_auth(access_token),
            params={"maxResults": count},
        )

        if list_resp.status_code != 200:
            return {"error": list_resp.text, "status_code": list_resp.status_code}

        messages = list_resp.json().get("messages", [])
        if not messages:
            return {"emails": []}

        # 2. Fetch all message details concurrently
        async def fetch_detail(msg_id: str) -> dict:
            resp = await client.get(
                f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}",
                headers=_auth(access_token),
                params={"format": "metadata", "metadataHeaders": ["Subject", "From"]},
            )
            if resp.status_code != 200:
                return {"error": resp.text, "id": msg_id}
            return resp.json()

        results = await asyncio.gather(
            *[fetch_detail(msg["id"]) for msg in messages]
        )

    return {"emails": list(results)}


# ── Google Calendar ───────────────────────────────────────────────────────────

async def create_calendar_event(access_token: str, params: dict) -> dict:
    # Validate required fields before making the network call
    start = params.get("start")
    end = params.get("end")
    if not start or not end:
        return {"error": "Both 'start' and 'end' datetime fields are required."}

    event_body = {
        "summary": params.get("title", "New Event"),
        "description": params.get("description", ""),
        "start": {"dateTime": start, "timeZone": params.get("timezone", "UTC")},
        "end":   {"dateTime": end,   "timeZone": params.get("timezone", "UTC")},
    }

    async with get_http_client() as client:
        resp = await client.post(
            "https://www.googleapis.com/calendar/v3/calendars/primary/events",
            headers=_auth(access_token),
            json=event_body,
        )

    if resp.status_code not in (200, 201):
        return {"error": resp.text, "status_code": resp.status_code}

    return resp.json()


# ── GitHub ────────────────────────────────────────────────────────────────────

GITHUB_API_VERSION = "2022-11-28"

async def create_github_issue(access_token: str, params: dict) -> dict:
    owner = params.get("owner")
    repo  = params.get("repo")

    if not owner or not repo:
        return {"error": "Both 'owner' and 'repo' are required."}

    async with get_http_client() as client:
        resp = await client.post(
            f"https://api.github.com/repos/{owner}/{repo}/issues",
            headers={
                **_auth(access_token),
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": GITHUB_API_VERSION,  # Required by GitHub
            },
            json={
                "title": params.get("title", "New Issue"),
                "body":  params.get("body", ""),
                "labels": params.get("labels", []),          # Bonus: label support
            },
        )

    if resp.status_code not in (200, 201):
        return {"error": resp.text, "status_code": resp.status_code}

    return resp.json()