from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request

from src.library.app import ClawhubImportError, LibraryApp
from src.library.core.schema import (
    ClawhubImport,
    SkillCreate,
    SkillFileDelete,
    SkillFileIn,
    SkillFileOut,
    SkillOut,
    SkillUpdate,
)

router = APIRouter()


def get_library(request: Request) -> LibraryApp:
    return request.app.state.library


@router.post("", response_model=SkillOut, status_code=201)
async def create_skill(
    body: SkillCreate,
    library: LibraryApp = Depends(get_library),
) -> SkillOut:
    record = await library.create(
        body.workspace_id,
        body.name,
        body.description,
        always=body.always,
        emoji=body.emoji,
        homepage=body.homepage,
        required_bins=body.required_bins,
        required_envs=body.required_envs,
        metadata_extra=body.metadata_extra,
    )
    return SkillOut(**record)


@router.patch("/{skill_id}", response_model=SkillOut)
async def update_skill(
    skill_id: UUID,
    body: SkillUpdate,
    library: LibraryApp = Depends(get_library),
) -> SkillOut:
    # exclude_unset lets the client explicitly clear nullable fields
    # (emoji/homepage) by sending `null`, while still ignoring fields
    # that weren't mentioned in the request at all.
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(400, "No fields to update")
    # `name` and list-valued fields don't accept null — guard them
    # so a stray null from a client doesn't violate NOT NULL.
    if updates.get("name") is None and "name" in updates:
        raise HTTPException(400, "name cannot be null")
    for list_field in ("required_bins", "required_envs"):
        if list_field in updates and updates[list_field] is None:
            raise HTTPException(400, f"{list_field} cannot be null")
    record = await library.update(skill_id, **updates)
    if not record:
        raise HTTPException(404, "Skill not found")
    return SkillOut(**record)


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
    if not await library.find_by_id(skill_id):
        raise HTTPException(404, "Skill not found")
    return SkillFileOut(**await library.upsert_file(skill_id, body.path, body.content))


@router.delete("/{skill_id}/files", status_code=204)
async def delete_skill_file(
    skill_id: UUID,
    body: SkillFileDelete,
    library: LibraryApp = Depends(get_library),
) -> None:
    if not await library.find_by_id(skill_id):
        raise HTTPException(404, "Skill not found")
    deleted = await library.delete_file(skill_id, body.path)
    if not deleted:
        raise HTTPException(404, "File not found")


@router.post("/import-clawhub", response_model=SkillOut, status_code=201)
async def import_from_clawhub(
    body: ClawhubImport,
    library: LibraryApp = Depends(get_library),
) -> SkillOut:
    try:
        record = await library.import_from_clawhub(body.workspace_id, body.url)
    except ClawhubImportError as exc:
        raise HTTPException(422, str(exc)) from exc
    return SkillOut(**record)
