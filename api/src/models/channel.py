from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class ChannelCreate(BaseModel):
    user_id: UUID
    type: str
    config: dict  # written, never returned


class ChannelOut(BaseModel):
    id: UUID
    user_id: UUID
    type: str
    created_at: datetime
    # config intentionally omitted
