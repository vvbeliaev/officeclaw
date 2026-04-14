from uuid import UUID

import asyncpg

from src.library.adapters.out.repository import SkillFileRepo, SkillRepo


class SkillService:
    def __init__(self, skill_repo: SkillRepo, skill_file_repo: SkillFileRepo) -> None:
        self._skills = skill_repo
        self._files = skill_file_repo

    async def create(self, workspace_id: UUID, name: str, description: str) -> asyncpg.Record:
        return await self._skills.create(workspace_id, name, description)

    async def find_by_id(self, skill_id: UUID) -> asyncpg.Record | None:
        return await self._skills.find_by_id(skill_id)

    async def list_by_workspace(self, workspace_id: UUID) -> list[asyncpg.Record]:
        return await self._skills.list_by_workspace(workspace_id)

    async def delete(self, skill_id: UUID) -> None:
        await self._skills.delete(skill_id)

    async def upsert_file(self, skill_id: UUID, path: str, content: str) -> asyncpg.Record:
        return await self._files.upsert(skill_id, path, content)

    async def list_files(self, skill_id: UUID) -> list[asyncpg.Record]:
        return await self._files.list_by_skill(skill_id)
