from pydantic import BaseModel


class AgentTaskRequest(BaseModel):
    action: str
    params: dict = {}


class StatusResponse(BaseModel):
    logged_in: bool
    user_id: str | None
    providers_linked: list[str]
    message: str
