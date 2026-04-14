from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class UserCreate(BaseModel):
    email: str


class UserRegistered(BaseModel):
    id: UUID
    email: str
    workspace_id: UUID
    officeclaw_token: str
    created_at: datetime


class BootstrapOut(BaseModel):
    workspace_id: UUID
    officeclaw_token: str
