# api/src/routers/users.py
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
import asyncpg
from src.db.pool import get_pool
from src.models.user import UserCreate, UserOut
from src.repositories.users import UserRepo

router = APIRouter()


def get_repo(pool: asyncpg.Connection = Depends(get_pool)) -> UserRepo:
    return UserRepo(pool)


@router.post("", response_model=UserOut, status_code=201)
async def create_user(body: UserCreate, repo: UserRepo = Depends(get_repo)) -> UserOut:
    try:
        record = await repo.create(body.email)
    except asyncpg.UniqueViolationError:
        raise HTTPException(409, "Email already registered")
    return UserOut(**dict(record))


@router.get("/{user_id}", response_model=UserOut)
async def get_user(user_id: UUID, repo: UserRepo = Depends(get_repo)) -> UserOut:
    record = await repo.find_by_id(user_id)
    if not record:
        raise HTTPException(404, "User not found")
    return UserOut(**dict(record))
