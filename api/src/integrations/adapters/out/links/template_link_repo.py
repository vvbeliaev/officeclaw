from uuid import UUID

import asyncpg


class TemplateLinkRepo:
    def __init__(self, conn: asyncpg.Pool) -> None:
        self._conn = conn

    async def attach(self, agent_id: UUID, template_id: UUID, template_type: str) -> None:
        # Upsert: replaces existing attachment of the same type for this agent.
        await self._conn.execute(
            "INSERT INTO agent_user_templates (agent_id, user_template_id, template_type)"
            " VALUES ($1, $2, $3)"
            " ON CONFLICT (agent_id, template_type)"
            " DO UPDATE SET user_template_id = EXCLUDED.user_template_id",
            agent_id, template_id, template_type,
        )

    async def detach(self, agent_id: UUID, template_id: UUID) -> None:
        await self._conn.execute(
            "DELETE FROM agent_user_templates"
            " WHERE agent_id = $1 AND user_template_id = $2",
            agent_id, template_id,
        )

    async def list_by_agent(self, agent_id: UUID) -> list[asyncpg.Record]:
        return await self._conn.fetch(
            "SELECT t.id, t.user_id, t.name, t.template_type, t.content, t.created_at"
            " FROM user_templates t"
            " JOIN agent_user_templates a ON a.user_template_id = t.id"
            " WHERE a.agent_id = $1",
            agent_id,
        )
