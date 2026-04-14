from uuid import UUID

import asyncpg

from src.integrations.adapters.out.env_repo import EnvRepo


class EnvService:
    def __init__(self, repo: EnvRepo) -> None:
        self._repo = repo

    async def create(self, workspace_id: UUID, name: str, values: dict, category: str | None = None) -> asyncpg.Record:
        return await self._repo.create(workspace_id, name, values, category)

    async def find(self, env_id: UUID) -> asyncpg.Record | None:
        return await self._repo.find_by_id(env_id)

    async def list(self, workspace_id: UUID) -> list[asyncpg.Record]:
        return await self._repo.list_by_workspace(workspace_id)

    async def get_decrypted(self, env_id: UUID) -> dict:
        return await self._repo.get_decrypted_values(env_id)

    async def update(
        self, env_id: UUID, name: str | None = None, values: dict | None = None, category: str | None = None
    ) -> asyncpg.Record | None:
        return await self._repo.update(env_id, name=name, values=values, category=category)

    async def delete(self, env_id: UUID) -> None:
        await self._repo.delete(env_id)

    async def find_llm_provider(self, workspace_id: UUID) -> asyncpg.Record | None:
        return await self._repo.find_llm_provider_by_workspace(workspace_id)
