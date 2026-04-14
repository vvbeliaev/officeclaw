import re
import uuid as _uuid_mod
from uuid import UUID

import asyncpg


def _slugify(name: str, uid_prefix: str) -> str:
    """Convert workspace name + uuid prefix into a URL-safe slug."""
    s = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    if len(s) > 40:
        s = s[:40].rstrip('-')
    if s:
        return f"{s}-{uid_prefix}"
    return uid_prefix


class WorkspaceRepo:
    def __init__(self, conn: asyncpg.Pool) -> None:
        self._conn = conn

    async def create(self, user_id: UUID, name: str, token: str) -> asyncpg.Record:
        workspace_id = _uuid_mod.uuid4()
        slug = _slugify(name, str(workspace_id)[:6])
        return await self._conn.fetchrow(
            "INSERT INTO workspaces (id, user_id, name, slug, officeclaw_token)"
            " VALUES ($1, $2, $3, $4, $5) RETURNING *",
            workspace_id, user_id, name, slug, token,
        )

    async def find_by_id(self, workspace_id: UUID) -> asyncpg.Record | None:
        return await self._conn.fetchrow(
            "SELECT * FROM workspaces WHERE id = $1", workspace_id
        )

    async def find_by_slug(self, slug: str) -> asyncpg.Record | None:
        return await self._conn.fetchrow(
            "SELECT * FROM workspaces WHERE slug = $1", slug
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

    async def update(
        self,
        workspace_id: UUID,
        name: str | None,
        slug: str | None,
    ) -> asyncpg.Record:
        parts = []
        values: list = []
        idx = 1
        if name is not None:
            parts.append(f"name = ${idx}")
            values.append(name)
            idx += 1
        if slug is not None:
            parts.append(f"slug = ${idx}")
            values.append(slug)
            idx += 1
        values.append(workspace_id)
        query = f"UPDATE workspaces SET {', '.join(parts)} WHERE id = ${idx} RETURNING *"
        return await self._conn.fetchrow(query, *values)

    async def delete(self, workspace_id: UUID) -> None:
        await self._conn.execute(
            "DELETE FROM workspaces WHERE id = $1", workspace_id
        )
