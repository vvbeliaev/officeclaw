# api/src/routers/users.py
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException

from src.admin import create_admin_for_user
from src.db.pool import get_pool
from src.models.user import UserCreate, UserOut, UserRegistered
from src.repositories.users import UserRepo

router = APIRouter()


def get_repo(conn: asyncpg.Connection = Depends(get_pool)) -> UserRepo:
    return UserRepo(conn)


@router.post("", response_model=UserRegistered, status_code=201)
async def create_user(
    body: UserCreate,
    conn: asyncpg.Connection = Depends(get_pool),
) -> UserRegistered:
    repo = UserRepo(conn)
    try:
        record = await repo.create(body.email)
    except asyncpg.UniqueViolationError:
        raise HTTPException(409, "Email already registered")
    token = await create_admin_for_user(conn, record["id"])
    return UserRegistered(
        id=record["id"],
        email=record["email"],
        created_at=record["created_at"],
        officeclaw_token=token,
    )


@router.get("/{user_id}", response_model=UserOut)
async def get_user(user_id: UUID, repo: UserRepo = Depends(get_repo)) -> UserOut:
    record = await repo.find_by_id(user_id)
    if not record:
        raise HTTPException(404, "User not found")
    return UserOut(**dict(record))
