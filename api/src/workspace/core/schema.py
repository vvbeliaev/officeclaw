from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class WorkspaceCreate(BaseModel):
    user_id: UUID
    name: str


class WorkspaceUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None


class WorkspaceOut(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    slug: str
    officeclaw_token: str
    created_at: datetime
