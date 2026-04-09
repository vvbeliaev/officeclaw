from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
import asyncpg
from src.db.pool import get_pool
from src.models.env import EnvCreate, EnvOut
from src.repositories.envs import EnvRepo

router = APIRouter()


def get_repo(pool: asyncpg.Connection = Depends(get_pool)) -> EnvRepo:
    return EnvRepo(pool)


@router.post("", response_model=EnvOut, status_code=201)
async def create_env(body: EnvCreate, repo: EnvRepo = Depends(get_repo)) -> EnvOut:
    try:
        record = await repo.create(body.user_id, body.name, body.values)
    except asyncpg.UniqueViolationError:
        raise HTTPException(409, "Env name already exists for this user")
    return EnvOut(**dict(record))


@router.get("", response_model=list[EnvOut])
async def list_envs(user_id: UUID, repo: EnvRepo = Depends(get_repo)) -> list[EnvOut]:
    return [EnvOut(**dict(r)) for r in await repo.list_by_user(user_id)]


@router.delete("/{env_id}", status_code=204)
async def delete_env(env_id: UUID, repo: EnvRepo = Depends(get_repo)) -> None:
    if not await repo.find_by_id(env_id):
        raise HTTPException(404, "Env not found")
    await repo.delete(env_id)
