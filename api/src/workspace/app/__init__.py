from uuid import UUID

import asyncpg

from src.workspace.app.workspaces import WorkspaceService


class WorkspaceApp:
    def __init__(self, service: WorkspaceService) -> None:
        self._service = service

    async def create_workspace(self, user_id: UUID, name: str) -> asyncpg.Record:
        return await self._service.create_workspace(user_id, name)

    async def list_workspaces(self, user_id: UUID) -> list[asyncpg.Record]:
        return await self._service.list_workspaces(user_id)

    async def find_by_token(self, token: str) -> asyncpg.Record | None:
        return await self._service.find_by_token(token)
