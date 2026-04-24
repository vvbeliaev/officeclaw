from uuid import UUID
from pydantic import BaseModel


class BootstrapOut(BaseModel):
    workspace_id: UUID
    officeclaw_token: str
