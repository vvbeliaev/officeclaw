# api/src/library/schema.py
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class SkillCreate(BaseModel):
    user_id: UUID
    name: str
    description: str = ""


class SkillOut(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    description: str
    created_at: datetime


class SkillFileIn(BaseModel):
    path: str
    content: str


class SkillFileOut(BaseModel):
    id: UUID
    skill_id: UUID
    path: str
    content: str
    updated_at: datetime
