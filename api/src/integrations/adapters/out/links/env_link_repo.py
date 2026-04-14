from uuid import UUID

import asyncpg


class EnvLinkRepo:
    def __init__(self, conn: asyncpg.Pool) -> None:
        self._conn = conn

    async def attach(self, agent_id: UUID, env_id: UUID) -> None:
        await self._conn.execute(
            "INSERT INTO agent_envs (agent_id, env_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
            agent_id, env_id,
        )

    async def detach(self, agent_id: UUID, env_id: UUID) -> None:
        await self._conn.execute(
            "DELETE FROM agent_envs WHERE agent_id = $1 AND env_id = $2", agent_id, env_id
        )

    async def list_by_agent(self, agent_id: UUID) -> list[asyncpg.Record]:
        return await self._conn.fetch(
            "SELECT e.id, e.workspace_id, e.name, e.created_at FROM workspace_envs e"
            " JOIN agent_envs a ON a.env_id = e.id WHERE a.agent_id = $1",
            agent_id,
        )
