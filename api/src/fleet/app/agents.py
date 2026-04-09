from uuid import UUID

import asyncpg

from src.fleet.adapters.out.repository import AgentFileRepo, AgentRepo


class AgentService:
    def __init__(self, agent_repo: AgentRepo, file_repo: AgentFileRepo) -> None:
        self._agents = agent_repo
        self._files = file_repo

    async def create(
        self, user_id: UUID, name: str, image: str, is_admin: bool = False
    ) -> asyncpg.Record:
        return await self._agents.create(user_id, name, image, is_admin)

    async def find_by_id(self, agent_id: UUID) -> asyncpg.Record | None:
        return await self._agents.find_by_id(agent_id)

    async def list_by_user(self, user_id: UUID) -> list[asyncpg.Record]:
        return await self._agents.list_by_user(user_id)

    async def update(self, agent_id: UUID, **fields: object) -> asyncpg.Record | None:
        return await self._agents.update(agent_id, **fields)

    async def delete(self, agent_id: UUID) -> None:
        await self._agents.delete(agent_id)

    async def upsert_file(self, agent_id: UUID, path: str, content: str) -> asyncpg.Record:
        return await self._files.upsert(agent_id, path, content)

    async def find_file(self, agent_id: UUID, path: str) -> asyncpg.Record | None:
        return await self._files.find(agent_id, path)

    async def list_files(self, agent_id: UUID) -> list[asyncpg.Record]:
        return await self._files.list_by_agent(agent_id)

    async def bulk_upsert_files(self, agent_id: UUID, files: list[dict]) -> None:
        await self._files.bulk_upsert(agent_id, files)
