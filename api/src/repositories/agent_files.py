# api/src/repositories/agent_files.py
from uuid import UUID
import asyncpg


class AgentFileRepo:
    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def upsert(self, agent_id: UUID, path: str, content: str) -> asyncpg.Record:
        return await self._conn.fetchrow(
            """INSERT INTO agent_files (agent_id, path, content)
               VALUES ($1, $2, $3)
               ON CONFLICT (agent_id, path)
               DO UPDATE SET content = EXCLUDED.content, updated_at = NOW()
               RETURNING *""",
            agent_id, path, content,
        )

    async def find(self, agent_id: UUID, path: str) -> asyncpg.Record | None:
        return await self._conn.fetchrow(
            "SELECT * FROM agent_files WHERE agent_id = $1 AND path = $2", agent_id, path
        )

    async def list_by_agent(self, agent_id: UUID) -> list[asyncpg.Record]:
        return await self._conn.fetch(
            "SELECT * FROM agent_files WHERE agent_id = $1 ORDER BY path", agent_id
        )

    async def bulk_upsert(self, agent_id: UUID, files: list[dict]) -> None:
        for f in files:
            await self.upsert(agent_id, f["path"], f["content"])
