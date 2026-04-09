# api/src/models/user.py
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr


class UserOut(BaseModel):
    id: UUID
    email: str
    created_at: datetime
