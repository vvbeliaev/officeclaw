from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr


class UserOut(BaseModel):
    id: UUID
    email: str
    created_at: datetime


class UserRegistered(BaseModel):
    id: UUID
    email: str
    created_at: datetime
    officeclaw_token: str  # shown once at registration, store it securely


class BootstrapOut(BaseModel):
    officeclaw_token: str
