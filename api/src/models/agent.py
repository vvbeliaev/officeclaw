# api/src/models/agent.py
from datetime import datetime
from uuid import UUID
from typing import Literal
from pydantic import BaseModel

AgentStatus = Literal["idle", "running", "error"]


class AgentCreate(BaseModel):
    user_id: UUID
    name: str
    image: str = "ghcr.io/hkuds/nanobot:latest"
    is_admin: bool = False


class AgentUpdate(BaseModel):
    name: str | None = None
    status: AgentStatus | None = None
    sandbox_id: str | None = None


class AgentOut(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    status: str
    sandbox_id: str | None
    image: str
    is_admin: bool
    created_at: datetime
    updated_at: datetime
