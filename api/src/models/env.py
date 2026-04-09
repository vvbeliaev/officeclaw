from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class EnvCreate(BaseModel):
    user_id: UUID
    name: str
    values: dict  # written, never read back


class EnvOut(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    created_at: datetime
    # values intentionally omitted
