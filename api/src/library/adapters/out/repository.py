# api/src/library/repository.py
from uuid import UUID
import asyncpg


class SkillRepo:
    def __init__(self, conn: asyncpg.Pool) -> None:
        self._conn = conn

    async def create(self, workspace_id: UUID, name: str, description: str) -> asyncpg.Record:
        return await self._conn.fetchrow(
            "INSERT INTO skills (workspace_id, name, description) VALUES ($1, $2, $3) RETURNING *",
            workspace_id, name, description,
        )

    async def find_by_id(self, skill_id: UUID) -> asyncpg.Record | None:
        return await self._conn.fetchrow("SELECT * FROM skills WHERE id = $1", skill_id)

    async def list_by_workspace(self, workspace_id: UUID) -> list[asyncpg.Record]:
        return await self._conn.fetch("SELECT * FROM skills WHERE workspace_id = $1", workspace_id)

    async def delete(self, skill_id: UUID) -> None:
        await self._conn.execute("DELETE FROM skills WHERE id = $1", skill_id)


class SkillFileRepo:
    def __init__(self, conn: asyncpg.Pool) -> None:
        self._conn = conn

    async def upsert(self, skill_id: UUID, path: str, content: str) -> asyncpg.Record:
        return await self._conn.fetchrow(
            """INSERT INTO skill_files (skill_id, path, content) VALUES ($1, $2, $3)
               ON CONFLICT (skill_id, path)
               DO UPDATE SET content = EXCLUDED.content, updated_at = NOW()
               RETURNING *""",
            skill_id, path, content,
        )

    async def list_by_skill(self, skill_id: UUID) -> list[asyncpg.Record]:
        return await self._conn.fetch(
            "SELECT * FROM skill_files WHERE skill_id = $1 ORDER BY path", skill_id
        )
