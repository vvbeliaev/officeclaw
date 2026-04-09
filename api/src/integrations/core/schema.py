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


class McpCreate(BaseModel):
    name: str
    config: dict  # {command, args} or {url, headers} -- never returned


class McpOut(BaseModel):
    id: UUID
    agent_id: UUID
    name: str
    # config intentionally omitted
