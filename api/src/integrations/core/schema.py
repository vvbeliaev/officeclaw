from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class EnvCreate(BaseModel):
    workspace_id: UUID
    name: str
    values: dict  # written, never read back
    category: str | None = None  # 'system' | 'llm-provider' | None


class EnvUpdate(BaseModel):
    name: str | None = None
    values: dict | None = None  # replaces encrypted blob when provided
    category: str | None = None


class EnvOut(BaseModel):
    id: UUID
    workspace_id: UUID
    name: str
    category: str | None = None
    created_at: datetime
    # values intentionally omitted


class EnvValuesOut(BaseModel):
    values: dict  # decrypted key-value pairs, returned only on explicit request


class ChannelCreate(BaseModel):
    workspace_id: UUID
    name: str
    type: str
    config: dict  # written, never returned


class ChannelOut(BaseModel):
    id: UUID
    workspace_id: UUID
    name: str
    type: str
    created_at: datetime
    # config intentionally omitted


class McpCreate(BaseModel):
    workspace_id: UUID
    name: str
    type: str   # 'stdio' | 'http'
    config: dict  # written, never returned


class McpOut(BaseModel):
    id: UUID
    workspace_id: UUID
    name: str
    type: str
    created_at: datetime
    # config intentionally omitted


class TemplateCreate(BaseModel):
    workspace_id: UUID
    name: str
    template_type: str  # 'user' | 'soul' | 'agents' | 'heartbeat' | 'tools'
    content: str = ''


class TemplateUpdate(BaseModel):
    name: str | None = None
    content: str | None = None


class TemplateOut(BaseModel):
    id: UUID
    workspace_id: UUID
    name: str
    template_type: str
    content: str
    created_at: datetime
    updated_at: datetime
