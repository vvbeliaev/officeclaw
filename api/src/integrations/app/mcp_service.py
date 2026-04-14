from uuid import UUID

import asyncpg

from src.integrations.adapters.out.mcp_repo import UserMcpRepo


class McpService:
    def __init__(self, repo: UserMcpRepo) -> None:
        self._repo = repo

    async def create(self, workspace_id: UUID, name: str, type_: str, config: dict) -> asyncpg.Record:
        return await self._repo.create(workspace_id, name, type_, config)

    async def find(self, mcp_id: UUID) -> asyncpg.Record | None:
        return await self._repo.find_by_id(mcp_id)

    async def list(self, workspace_id: UUID) -> list[asyncpg.Record]:
        return await self._repo.list_by_workspace(workspace_id)

    async def get_decrypted(self, mcp_id: UUID) -> dict:
        return await self._repo.get_decrypted_config(mcp_id)

    async def update(self, mcp_id: UUID, name: str | None = None, config: dict | None = None) -> asyncpg.Record | None:
        return await self._repo.update(mcp_id, name=name, config=config)

    async def delete(self, mcp_id: UUID) -> None:
        await self._repo.delete(mcp_id)
