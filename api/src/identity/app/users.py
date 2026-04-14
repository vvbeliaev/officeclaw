"""UserService — identity app layer. Delegates bootstrap to WorkspaceApp."""
from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

import asyncpg

from src.identity.adapters.out.repository import UserRepo

if TYPE_CHECKING:
    from src.workspace.app import WorkspaceApp


class UserService:
    def __init__(self, user_repo: UserRepo, workspace: WorkspaceApp) -> None:
        self._users = user_repo
        self._workspace = workspace

    async def create(self, email: str) -> asyncpg.Record:
        return await self._users.create(email)

    async def find_by_id(self, user_id: UUID) -> asyncpg.Record | None:
        return await self._users.find_by_id(user_id)

    async def register(self, email: str) -> tuple[asyncpg.Record, asyncpg.Record]:
        """Create user + bootstrap default workspace. Returns (user_record, workspace_record)."""
        user = await self._users.create(email)
        workspace = await self._workspace.create_workspace(user["id"], "Personal")
        return user, workspace

    async def bootstrap(self, user_id: UUID) -> asyncpg.Record:
        """Bootstrap Personal workspace for a user created by better-auth. Returns workspace record."""
        user = await self._users.find_by_id(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        return await self._workspace.create_workspace(user_id, "Personal")
