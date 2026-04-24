# api/src/library/schema.py
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class SkillCreate(BaseModel):
    workspace_id: UUID
    name: str
    description: str = ""
    always: bool = False
    emoji: str | None = None
    homepage: str | None = None
    required_bins: list[str] = Field(default_factory=list)
    required_envs: list[str] = Field(default_factory=list)
    metadata_extra: dict[str, Any] = Field(default_factory=dict)


class SkillUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    always: bool | None = None
    emoji: str | None = None
    homepage: str | None = None
    required_bins: list[str] | None = None
    required_envs: list[str] | None = None
    metadata_extra: dict[str, Any] | None = None


class SkillOut(BaseModel):
    id: UUID
    workspace_id: UUID
    name: str
    description: str
    always: bool
    emoji: str | None
    homepage: str | None
    required_bins: list[str]
    required_envs: list[str]
    metadata_extra: dict[str, Any]
    created_at: datetime


class SkillFileIn(BaseModel):
    path: str
    content: str


class SkillFileDelete(BaseModel):
    path: str


class SkillFileOut(BaseModel):
    id: UUID
    skill_id: UUID
    path: str
    content: str
    updated_at: datetime


class ClawhubImport(BaseModel):
    workspace_id: UUID
    url: str
