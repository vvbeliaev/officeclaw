from uuid import UUID
import asyncpg


class LinkRepo:
    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def attach_skill(self, agent_id: UUID, skill_id: UUID) -> None:
        await self._conn.execute(
            "INSERT INTO agent_skills (agent_id, skill_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
            agent_id, skill_id,
        )

    async def detach_skill(self, agent_id: UUID, skill_id: UUID) -> None:
        await self._conn.execute(
            "DELETE FROM agent_skills WHERE agent_id = $1 AND skill_id = $2", agent_id, skill_id
        )

    async def list_skills(self, agent_id: UUID) -> list[asyncpg.Record]:
        return await self._conn.fetch(
            "SELECT s.* FROM skills s JOIN agent_skills a ON a.skill_id = s.id WHERE a.agent_id = $1",
            agent_id,
        )

    async def attach_env(self, agent_id: UUID, env_id: UUID) -> None:
        await self._conn.execute(
            "INSERT INTO agent_envs (agent_id, env_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
            agent_id, env_id,
        )

    async def detach_env(self, agent_id: UUID, env_id: UUID) -> None:
        await self._conn.execute(
            "DELETE FROM agent_envs WHERE agent_id = $1 AND env_id = $2", agent_id, env_id
        )

    async def list_envs(self, agent_id: UUID) -> list[asyncpg.Record]:
        return await self._conn.fetch(
            "SELECT e.* FROM user_envs e JOIN agent_envs a ON a.env_id = e.id WHERE a.agent_id = $1",
            agent_id,
        )

    async def attach_channel(self, agent_id: UUID, channel_id: UUID) -> None:
        await self._conn.execute(
            "INSERT INTO agent_channels (agent_id, channel_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
            agent_id, channel_id,
        )

    async def detach_channel(self, agent_id: UUID, channel_id: UUID) -> None:
        await self._conn.execute(
            "DELETE FROM agent_channels WHERE agent_id = $1 AND channel_id = $2", agent_id, channel_id
        )

    async def list_channels(self, agent_id: UUID) -> list[asyncpg.Record]:
        return await self._conn.fetch(
            "SELECT c.* FROM user_channels c JOIN agent_channels a ON a.channel_id = c.id WHERE a.agent_id = $1",
            agent_id,
        )
