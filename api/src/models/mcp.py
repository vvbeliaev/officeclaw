from uuid import UUID
from pydantic import BaseModel


class McpCreate(BaseModel):
    name: str
    config: dict  # {command, args} or {url, headers} — never returned


class McpOut(BaseModel):
    id: UUID
    agent_id: UUID
    name: str
    # config intentionally omitted
