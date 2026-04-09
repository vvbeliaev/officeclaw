from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Request

from src.identity.app import IdentityApp
from src.identity.core.schema import UserCreate, UserOut, UserRegistered

router = APIRouter()


def get_identity(request: Request) -> IdentityApp:
    return request.app.state.identity


@router.post("", response_model=UserRegistered, status_code=201)
async def create_user(
    body: UserCreate,
    identity: IdentityApp = Depends(get_identity),
) -> UserRegistered:
    try:
        record, token = await identity.register(body.email)
    except asyncpg.UniqueViolationError:
        raise HTTPException(409, "Email already registered")
    return UserRegistered(
        id=record["id"],
        email=record["email"],
        created_at=record["created_at"],
        officeclaw_token=token,
    )


@router.get("/{user_id}", response_model=UserOut)
async def get_user(
    user_id: UUID,
    identity: IdentityApp = Depends(get_identity),
) -> UserOut:
    record = await identity.find_by_id(user_id)
    if not record:
        raise HTTPException(404, "User not found")
    return UserOut(**dict(record))
