from uuid import UUID
import asyncpg


_ALLOWED_UPDATE_FIELDS = frozenset({"name", "status", "sandbox_id", "gateway_port"})


class AgentRepo:
    def __init__(self, conn: asyncpg.Pool) -> None:
        self._conn = conn

    async def create(
        self, user_id: UUID, name: str, image: str, is_admin: bool
    ) -> asyncpg.Record:
        return await self._conn.fetchrow(
            "INSERT INTO agents (user_id, name, image, is_admin) VALUES ($1, $2, $3, $4) RETURNING *",
            user_id,
            name,
            image,
            is_admin,
        )

    async def find_by_id(self, agent_id: UUID) -> asyncpg.Record | None:
        return await self._conn.fetchrow("SELECT * FROM agents WHERE id = $1", agent_id)

    async def list_by_user(self, user_id: UUID) -> list[asyncpg.Record]:
        return await self._conn.fetch(
            "SELECT * FROM agents WHERE user_id = $1", user_id
        )

    async def update(self, agent_id: UUID, **fields) -> asyncpg.Record | None:
        unknown = set(fields) - _ALLOWED_UPDATE_FIELDS
        if unknown:
            raise ValueError(f"Unknown agent fields: {unknown}")
        set_clauses = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(fields))
        values = list(fields.values())
        return await self._conn.fetchrow(
            f"UPDATE agents SET {set_clauses}, updated_at = NOW() WHERE id = $1 RETURNING *",
            agent_id,
            *values,
        )

    async def delete(self, agent_id: UUID) -> None:
        await self._conn.execute("DELETE FROM agents WHERE id = $1", agent_id)


class AgentFileRepo:
    def __init__(self, conn: asyncpg.Pool) -> None:
        self._conn = conn

    async def upsert(self, agent_id: UUID, path: str, content: str) -> asyncpg.Record:
        return await self._conn.fetchrow(
            """INSERT INTO agent_files (agent_id, path, content)
               VALUES ($1, $2, $3)
               ON CONFLICT (agent_id, path)
               DO UPDATE SET content = EXCLUDED.content, updated_at = NOW()
               RETURNING *""",
            agent_id,
            path,
            content,
        )

    async def find(self, agent_id: UUID, path: str) -> asyncpg.Record | None:
        return await self._conn.fetchrow(
            "SELECT * FROM agent_files WHERE agent_id = $1 AND path = $2",
            agent_id,
            path,
        )

    async def list_by_agent(self, agent_id: UUID) -> list[asyncpg.Record]:
        return await self._conn.fetch(
            "SELECT * FROM agent_files WHERE agent_id = $1 ORDER BY path", agent_id
        )

    async def bulk_upsert(self, agent_id: UUID, files: list[dict]) -> None:
        for f in files:
            await self.upsert(agent_id, f["path"], f["content"])
