# SecureProxy

> An authentication layer that acts as a secure intermediary between your identity and the tools you use — Gmail, Google Calendar, GitHub, Slack, and more.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com)
[![Auth0](https://img.shields.io/badge/Auth0-Token%20Vault-orange.svg)](https://auth0.com)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

---

## What is SecureProxy?

SecureProxy is a FastAPI-based authentication proxy that handles OAuth token management for third-party integrations. Instead of managing tokens manually across multiple services, SecureProxy authenticates users via Auth0 and acts as a secure middleman — fetching, storing, and refreshing OAuth tokens so your app can talk to Gmail, Google Calendar, GitHub, and other services without ever exposing credentials.

Built for the **Auth0 Hackathon**.

🔗 **Repo**: [github.com/muzakkir2045/secure-proxy](https://github.com/muzakkir2045/secure-proxy)

---

## Features

- 🔐 **Auth0 Authentication** — Secure login via Auth0 with session management
- 📬 **Gmail Integration** — Fetch emails with metadata (subject, sender, labels)
- 📅 **Google Calendar Integration** — Create and manage calendar events
- 🐙 **GitHub Integration** — Create issues on any repository
- 🏦 **Token Vault Support** — Auth0 Token Vault for secure provider token storage
- 🔄 **Session Fallback** — Graceful fallback to session storage when vault isn't available
- ⚡ **Concurrent Requests** — Parallel email fetching via `asyncio.gather`
- 🛡️ **Input Validation** — Request validation with Pydantic models
- ⏱️ **Timeout Handling** — Configurable timeouts on all HTTP calls

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+, FastAPI |
| Auth | Auth0 (Authorization Code Flow + Token Vault) |
| HTTP Client | httpx (async) |
| Session | Starlette SessionMiddleware |
| Token Storage | Auth0 Token Vault + session fallback |

---

## Project Structure

```
secure-proxy/
├── main.py              # FastAPI app, routes, token vault logic
├── auth.py              # /connect/{provider} OAuth connection routes
├── api_clients.py       # Gmail, Google Calendar, GitHub API calls
├── frontend/
│   └── index.html       # Frontend UI
├── .env                 # Environment variables (never commit this)
├── requirements.txt     # Python dependencies
└── README.md
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- An [Auth0](https://auth0.com) account
- A Google Cloud project with Gmail and Calendar APIs enabled
- A GitHub OAuth App

### 1. Clone the repo

```bash
git clone https://github.com/muzakkir2045/secure-proxy.git
cd secure-proxy
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Create a `.env` file in the project root:

```env
# Auth0
AUTH0_DOMAIN=your-tenant.eu.auth0.com
AUTH0_CLIENT_ID=your_client_id
AUTH0_CLIENT_SECRET=your_client_secret
AUTH0_AUDIENCE=https://your-tenant.eu.auth0.com/api/v2/

# App
BASE_URL=http://localhost:8000
APP_SECRET_KEY=your_random_secret_key

# Google (for refresh token flow)
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
```

Generate a secure `APP_SECRET_KEY`:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 4. Auth0 Dashboard Setup

**Application Settings:**
- Type: Regular Web Application
- Allowed Callback URLs: `http://localhost:8000/callback`
- Allowed Logout URLs: `http://localhost:8000`

**Grant Types** (`Applications → Your App → Advanced Settings → Grant Types`):
- ✅ Authorization Code
- ✅ Refresh Token
- ✅ Client Credentials
- ✅ Token Vault

**Social Connections** (`Authentication → Social`):
- Enable `google-oauth2` with Gmail + Calendar scopes
- Enable `github` with `read:user`, `public_repo`, `repo` scopes
- Turn on **Store Access Tokens** for both connections

**Management API** (`Applications → APIs → Auth0 Management API → Machine to Machine Applications`):
- Enable SecureProxy with scopes: `read:users`, `read:user_idp_tokens`

### 5. Run the app

```bash
uvicorn main:app --reload
```

Visit `http://localhost:8000`

---

## Usage

### Authentication Flow

```
1. Visit /login              → Auth0 login
2. Visit /connect/gmail      → Connect Gmail + Google Calendar
3. Visit /connect/github     → Connect GitHub
```

Or use the one-click connect page:
```
http://localhost:8000/connect/all
```

### Agent Task API

All integrations are exposed via a single endpoint:

```
POST /agent/task
```

**Fetch Emails:**
```json
{
  "action": "fetch_emails",
  "params": { "count": 5 }
}
```

**Create Calendar Event:**
```json
{
  "action": "create_calendar_event",
  "params": {
    "title": "Team Standup",
    "start": "2026-04-01T10:00:00Z",
    "end": "2026-04-01T10:30:00Z",
    "timezone": "Asia/Kolkata"
  }
}
```

**Create GitHub Issue:**
```json
{
  "action": "create_github_issue",
  "params": {
    "owner": "your-username",
    "repo": "your-repo",
    "title": "Bug: login flow broken",
    "body": "Steps to reproduce...",
    "labels": ["bug"]
  }
}
```

### Other Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Frontend UI |
| `/login` | GET | Initiate Auth0 login |
| `/logout` | GET | Clear session and logout |
| `/callback` | GET | Auth0 OAuth callback |
| `/connect/{provider}` | GET | Connect a provider (`gmail`, `google-calendar`, `github`) |
| `/connect/all` | GET | One-click connect page for all providers |
| `/status` | GET | Check login state and connected providers |

---

## Token Management

SecureProxy uses a two-layer token strategy:

```
Request for provider token
        │
        ▼
1. Try Auth0 Token Vault  →  validate token  →  ✅ return if valid
        │
        ▼ (if vault fails or token expired)
2. Try session storage    →  ✅ return if present
        │
        ▼ (if both fail)
3. Raise 403 → redirect to /connect/{provider}
```

Tokens are automatically validated before use. If a Google token is expired, the app attempts a refresh using the stored refresh token before falling back to re-authentication.

---

## Environment Variables Reference

| Variable | Required | Description |
|---|---|---|
| `AUTH0_DOMAIN` | ✅ | Your Auth0 tenant domain |
| `AUTH0_CLIENT_ID` | ✅ | Auth0 application client ID |
| `AUTH0_CLIENT_SECRET` | ✅ | Auth0 application client secret |
| `AUTH0_AUDIENCE` | ✅ | Auth0 Management API audience URL |
| `BASE_URL` | ✅ | Your app's base URL |
| `APP_SECRET_KEY` | ✅ | Secret key for session signing |
| `GOOGLE_CLIENT_ID` | ⚠️ | Required for Google token refresh |
| `GOOGLE_CLIENT_SECRET` | ⚠️ | Required for Google token refresh |

---

## Security Notes

- Never commit your `.env` file — add it to `.gitignore`
- `APP_SECRET_KEY` must be a long random string in production
- Set `allow_origins` in CORS middleware to your actual domain in production (not `*`)
- OAuth tokens are stored server-side in sessions, never exposed to the frontend

---

## License

MIT
