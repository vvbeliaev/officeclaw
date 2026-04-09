# api/src/repositories/agents.py
from uuid import UUID
import asyncpg


_ALLOWED_UPDATE_FIELDS = frozenset({"name", "status", "sandbox_id"})


class AgentRepo:
    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def create(self, user_id: UUID, name: str, image: str, is_admin: bool) -> asyncpg.Record:
        return await self._conn.fetchrow(
            "INSERT INTO agents (user_id, name, image, is_admin) VALUES ($1, $2, $3, $4) RETURNING *",
            user_id, name, image, is_admin,
        )

    async def find_by_id(self, agent_id: UUID) -> asyncpg.Record | None:
        return await self._conn.fetchrow("SELECT * FROM agents WHERE id = $1", agent_id)

    async def list_by_user(self, user_id: UUID) -> list[asyncpg.Record]:
        return await self._conn.fetch("SELECT * FROM agents WHERE user_id = $1", user_id)

    async def update(self, agent_id: UUID, **fields) -> asyncpg.Record | None:
        unknown = set(fields) - _ALLOWED_UPDATE_FIELDS
        if unknown:
            raise ValueError(f"Unknown agent fields: {unknown}")
        set_clauses = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(fields))
        values = list(fields.values())
        return await self._conn.fetchrow(
            f"UPDATE agents SET {set_clauses}, updated_at = NOW() WHERE id = $1 RETURNING *",
            agent_id, *values,
        )

    async def delete(self, agent_id: UUID) -> None:
        await self._conn.execute("DELETE FROM agents WHERE id = $1", agent_id)
