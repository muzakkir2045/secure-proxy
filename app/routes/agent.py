from fastapi import APIRouter, Request, HTTPException

from app.models.schemas import AgentTaskRequest
from app.services.token_manager import get_vault_token
from app.services import api_clients

router = APIRouter()


@router.post("/agent/task")
async def agent_task(request: Request, body: AgentTaskRequest):
    if not request.session.get("logged_in"):
        raise HTTPException(status_code=401, detail="Not authenticated")

    action = body.action
    params = body.params

    if "action" in params and "params" in params:
        print("[AgentTask] Detected double-nested body, unwrapping...")
        action = params.get("action", action)
        params = params.get("params", {})

    print(f"[AgentTask] action={action}, params={params}")

    if action == "fetch_emails":
        token = await get_vault_token(request, "gmail")
        return await api_clients.fetch_emails(token, params)

    elif action == "create_calendar_event":
        token = await get_vault_token(request, "google-calendar")
        return await api_clients.create_calendar_event(token, params)

    elif action == "create_github_issue":
        token = await get_vault_token(request, "github")
        return await api_clients.create_github_issue(token, params)

    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {action}")
