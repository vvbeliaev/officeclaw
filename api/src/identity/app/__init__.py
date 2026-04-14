from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

import asyncpg

from src.identity.app.users import UserService

if TYPE_CHECKING:
    from src.workspace.app import WorkspaceApp


class IdentityApp:
    def __init__(self, service: UserService) -> None:
        self._service = service

    async def register(self, email: str) -> tuple[asyncpg.Record, asyncpg.Record]:
        return await self._service.register(email)

    async def find_by_id(self, user_id: UUID) -> asyncpg.Record | None:
        return await self._service.find_by_id(user_id)

    async def bootstrap(self, user_id: UUID) -> asyncpg.Record:
        return await self._service.bootstrap(user_id)
