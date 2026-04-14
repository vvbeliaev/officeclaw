from uuid import UUID

import asyncpg

from src.integrations.adapters.out.template_repo import UserTemplateRepo


class TemplateService:
    def __init__(self, repo: UserTemplateRepo) -> None:
        self._repo = repo

    async def create(self, workspace_id: UUID, name: str, template_type: str, content: str) -> asyncpg.Record:
        return await self._repo.create(workspace_id, name, template_type, content)

    async def find(self, template_id: UUID) -> asyncpg.Record | None:
        return await self._repo.find_by_id(template_id)

    async def list(self, workspace_id: UUID) -> list[asyncpg.Record]:
        return await self._repo.list_by_workspace(workspace_id)

    async def update(
        self, template_id: UUID, name: str | None = None, content: str | None = None
    ) -> asyncpg.Record | None:
        return await self._repo.update(template_id, name=name, content=content)

    async def delete(self, template_id: UUID) -> None:
        await self._repo.delete(template_id)
