from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request

from src.library.app import LibraryApp
from src.library.core.schema import SkillCreate, SkillFileIn, SkillFileOut, SkillOut

router = APIRouter()


def get_library(request: Request) -> LibraryApp:
    return request.app.state.library


@router.post("", response_model=SkillOut, status_code=201)
async def create_skill(
    body: SkillCreate,
    library: LibraryApp = Depends(get_library),
) -> SkillOut:
    return SkillOut(**dict(await library.create(body.user_id, body.name, body.description)))


@router.delete("/{skill_id}", status_code=204)
async def delete_skill(
    skill_id: UUID,
    library: LibraryApp = Depends(get_library),
) -> None:
    if not await library.find_by_id(skill_id):
        raise HTTPException(404, "Skill not found")
    await library.delete(skill_id)


@router.put("/{skill_id}/files", response_model=SkillFileOut)
async def upsert_skill_file(
    skill_id: UUID,
    body: SkillFileIn,
    library: LibraryApp = Depends(get_library),
) -> SkillFileOut:
    return SkillFileOut(**dict(await library.upsert_file(skill_id, body.path, body.content)))
