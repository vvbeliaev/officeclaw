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

    async def find_by_id(self, user_id: UUID) -> asyncpg.Record | None:
        return await self._users.find_by_id(user_id)

    async def bootstrap(self, user_id: UUID) -> asyncpg.Record:
        """Idempotently bootstrap a Personal workspace for a user created by
        better-auth. If the user already has a workspace (e.g. a previous
        request succeeded but its response was lost and the web hook retried),
        return the existing one instead of creating a duplicate.
        """
        user = await self._users.find_by_id(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        existing = await self._workspace.list_workspaces(user_id)
        if existing:
            return existing[0]
        return await self._workspace.create_workspace(user_id, "Personal")
