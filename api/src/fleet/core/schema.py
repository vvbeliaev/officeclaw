from datetime import datetime
from uuid import UUID
from typing import Literal
from pydantic import BaseModel, Field

AgentStatus = Literal["idle", "running", "error"]


class AgentCreate(BaseModel):
    workspace_id: UUID
    name: str
    image: str = "localhost:5005/officeclaw/agent:latest"
    is_admin: bool = False


class AgentUpdate(BaseModel):
    name: str | None = None
    status: AgentStatus | None = None
    sandbox_id: str | None = None
    avatar_url: str | None = None
    skill_evolution: bool | None = None
    heartbeat_enabled: bool | None = None
    heartbeat_interval_s: int | None = Field(default=None, ge=60, le=86_400)


class AgentOut(BaseModel):
    id: UUID
    workspace_id: UUID
    name: str
    status: str
    sandbox_id: str | None
    gateway_port: int | None
    image: str
    is_admin: bool
    avatar_url: str | None
    skill_evolution: bool
    heartbeat_enabled: bool
    heartbeat_interval_s: int
    created_at: datetime
    updated_at: datetime


class AgentFileIn(BaseModel):
    path: str
    content: str


class AgentFileOut(BaseModel):
    id: UUID
    agent_id: UUID
    path: str
    content: str
    updated_at: datetime
