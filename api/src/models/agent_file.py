# api/src/models/agent_file.py
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class AgentFileIn(BaseModel):
    path: str
    content: str


class AgentFileOut(BaseModel):
    id: UUID
    agent_id: UUID
    path: str
    content: str
    updated_at: datetime
