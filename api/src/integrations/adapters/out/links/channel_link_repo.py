from uuid import UUID

import asyncpg


class ChannelLinkRepo:
    def __init__(self, conn: asyncpg.Pool) -> None:
        self._conn = conn

    async def attach(self, agent_id: UUID, channel_id: UUID) -> None:
        # ON CONFLICT ON CONSTRAINT covers only the PK (same agent re-attaching same channel
        # is idempotent). A unique violation on channel_id alone (different agent) propagates.
        await self._conn.execute(
            "INSERT INTO agent_channels (agent_id, channel_id) VALUES ($1, $2)"
            " ON CONFLICT ON CONSTRAINT agent_channels_pkey DO NOTHING",
            agent_id, channel_id,
        )

    async def detach(self, agent_id: UUID, channel_id: UUID) -> None:
        await self._conn.execute(
            "DELETE FROM agent_channels WHERE agent_id = $1 AND channel_id = $2", agent_id, channel_id
        )

    async def list_by_agent(self, agent_id: UUID) -> list[asyncpg.Record]:
        return await self._conn.fetch(
            "SELECT c.id, c.workspace_id, c.type, c.created_at FROM workspace_channels c"
            " JOIN agent_channels a ON a.channel_id = c.id WHERE a.agent_id = $1",
            agent_id,
        )
