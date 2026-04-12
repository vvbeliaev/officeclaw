from uuid import UUID

import asyncpg


class SkillLinkRepo:
    def __init__(self, conn: asyncpg.Pool) -> None:
        self._conn = conn

    async def attach(self, agent_id: UUID, skill_id: UUID) -> None:
        await self._conn.execute(
            "INSERT INTO agent_skills (agent_id, skill_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
            agent_id, skill_id,
        )

    async def detach(self, agent_id: UUID, skill_id: UUID) -> None:
        await self._conn.execute(
            "DELETE FROM agent_skills WHERE agent_id = $1 AND skill_id = $2", agent_id, skill_id
        )

    async def list_by_agent(self, agent_id: UUID) -> list[asyncpg.Record]:
        return await self._conn.fetch(
            "SELECT s.* FROM skills s JOIN agent_skills a ON a.skill_id = s.id WHERE a.agent_id = $1",
            agent_id,
        )
