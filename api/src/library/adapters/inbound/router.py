# api/src/routers/skills.py
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
import asyncpg
from src.shared.db.pool import get_pool
from src.library.core.schema import SkillCreate, SkillOut, SkillFileIn, SkillFileOut
from src.library.adapters.outbound.repository import SkillRepo, SkillFileRepo

router = APIRouter()


def get_repo(pool: asyncpg.Connection = Depends(get_pool)) -> SkillRepo:
    return SkillRepo(pool)


def get_file_repo(pool: asyncpg.Connection = Depends(get_pool)) -> SkillFileRepo:
    return SkillFileRepo(pool)


@router.post("", response_model=SkillOut, status_code=201)
async def create_skill(body: SkillCreate, repo: SkillRepo = Depends(get_repo)) -> SkillOut:
    return SkillOut(**dict(await repo.create(body.user_id, body.name, body.description)))


@router.get("", response_model=list[SkillOut])
async def list_skills(user_id: UUID, repo: SkillRepo = Depends(get_repo)) -> list[SkillOut]:
    return [SkillOut(**dict(r)) for r in await repo.list_by_user(user_id)]


@router.get("/{skill_id}", response_model=SkillOut)
async def get_skill(skill_id: UUID, repo: SkillRepo = Depends(get_repo)) -> SkillOut:
    record = await repo.find_by_id(skill_id)
    if not record:
        raise HTTPException(404, "Skill not found")
    return SkillOut(**dict(record))


@router.delete("/{skill_id}", status_code=204)
async def delete_skill(skill_id: UUID, repo: SkillRepo = Depends(get_repo)) -> None:
    if not await repo.find_by_id(skill_id):
        raise HTTPException(404, "Skill not found")
    await repo.delete(skill_id)


@router.put("/{skill_id}/files", response_model=SkillFileOut)
async def upsert_skill_file(
    skill_id: UUID, body: SkillFileIn, repo: SkillFileRepo = Depends(get_file_repo)
) -> SkillFileOut:
    return SkillFileOut(**dict(await repo.upsert(skill_id, body.path, body.content)))


@router.get("/{skill_id}/files", response_model=list[SkillFileOut])
async def list_skill_files(
    skill_id: UUID, repo: SkillFileRepo = Depends(get_file_repo)
) -> list[SkillFileOut]:
    return [SkillFileOut(**dict(r)) for r in await repo.list_by_skill(skill_id)]
