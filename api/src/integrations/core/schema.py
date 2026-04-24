from datetime import datetime
from typing import Any, Literal
from uuid import UUID
from pydantic import BaseModel, Field, model_validator

CronKind = Literal["at", "every", "cron"]
CronStatus = Literal["ok", "error", "skipped"]


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


class ChannelUpdate(BaseModel):
    name: str | None = None
    config: dict | None = None  # replaces encrypted blob when provided


class ChannelOut(BaseModel):
    id: UUID
    workspace_id: UUID
    name: str
    type: str
    created_at: datetime
    # config intentionally omitted


class ChannelConfigOut(BaseModel):
    config: dict  # decrypted config, returned only on explicit request


class McpCreate(BaseModel):
    workspace_id: UUID
    name: str
    type: str   # 'stdio' | 'http'
    config: dict  # written, never returned


class McpUpdate(BaseModel):
    name: str | None = None
    config: dict | None = None  # replaces encrypted blob when provided


class McpOut(BaseModel):
    id: UUID
    workspace_id: UUID
    name: str
    type: str
    created_at: datetime
    # config intentionally omitted


class McpConfigOut(BaseModel):
    config: dict  # decrypted config, returned only on explicit request


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


class CronCreate(BaseModel):
    workspace_id: UUID
    name: str
    schedule_kind: CronKind
    schedule_at_ms: int | None = None
    schedule_every_ms: int | None = Field(default=None, ge=1000)
    schedule_expr: str | None = None
    schedule_tz: str | None = None
    message: str = ""
    deliver: bool = False
    channel: str | None = None
    recipient: str | None = None
    delete_after_run: bool = False

    @model_validator(mode="after")
    def _check_schedule_shape(self) -> "CronCreate":
        if self.schedule_kind == "at" and self.schedule_at_ms is None:
            raise ValueError("schedule_at_ms required for kind='at'")
        if self.schedule_kind == "every" and not self.schedule_every_ms:
            raise ValueError("schedule_every_ms required for kind='every'")
        if self.schedule_kind == "cron" and not self.schedule_expr:
            raise ValueError("schedule_expr required for kind='cron'")
        if self.schedule_tz and self.schedule_kind != "cron":
            raise ValueError("schedule_tz only applies to kind='cron'")
        return self


class CronUpdate(BaseModel):
    name: str | None = None
    schedule_kind: CronKind | None = None
    schedule_at_ms: int | None = None
    schedule_every_ms: int | None = Field(default=None, ge=1000)
    schedule_expr: str | None = None
    schedule_tz: str | None = None
    message: str | None = None
    deliver: bool | None = None
    channel: str | None = None
    recipient: str | None = None
    delete_after_run: bool | None = None


class CronOut(BaseModel):
    id: UUID
    workspace_id: UUID
    name: str
    schedule_kind: CronKind
    schedule_at_ms: int | None = None
    schedule_every_ms: int | None = None
    schedule_expr: str | None = None
    schedule_tz: str | None = None
    message: str
    deliver: bool
    channel: str | None = None
    recipient: str | None = None
    delete_after_run: bool
    created_at: datetime
    updated_at: datetime


class AgentCronOut(BaseModel):
    agent_id: UUID
    cron_id: UUID
    enabled: bool
    next_run_at_ms: int | None = None
    last_run_at_ms: int | None = None
    last_status: CronStatus | None = None
    last_error: str | None = None
    run_history: list[dict[str, Any]] = []


class AgentCronWithCronOut(CronOut):
    enabled: bool
    next_run_at_ms: int | None = None
    last_run_at_ms: int | None = None
    last_status: CronStatus | None = None
    last_error: str | None = None
    run_history: list[dict[str, Any]] = []


class AgentCronUpdate(BaseModel):
    enabled: bool | None = None
