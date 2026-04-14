from uuid import UUID

import asyncpg


class WorkspaceRepo:
    def __init__(self, conn: asyncpg.Pool) -> None:
        self._conn = conn

    async def create(self, user_id: UUID, name: str, token: str) -> asyncpg.Record:
        return await self._conn.fetchrow(
            "INSERT INTO workspaces (user_id, name, officeclaw_token)"
            " VALUES ($1, $2, $3) RETURNING *",
            user_id, name, token,
        )

    async def find_by_id(self, workspace_id: UUID) -> asyncpg.Record | None:
        return await self._conn.fetchrow(
            "SELECT * FROM workspaces WHERE id = $1", workspace_id
        )

    async def find_by_token(self, token: str) -> asyncpg.Record | None:
        return await self._conn.fetchrow(
            "SELECT * FROM workspaces WHERE officeclaw_token = $1", token
        )

    async def list_by_user(self, user_id: UUID) -> list[asyncpg.Record]:
        return await self._conn.fetch(
            "SELECT * FROM workspaces WHERE user_id = $1 ORDER BY created_at ASC",
            user_id,
        )
