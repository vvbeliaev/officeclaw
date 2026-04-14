from uuid import UUID

import asyncpg

from src.shared.crypto import decrypt_json


class McpLinkRepo:
    def __init__(self, conn: asyncpg.Pool) -> None:
        self._conn = conn

    async def attach(self, agent_id: UUID, mcp_id: UUID) -> None:
        await self._conn.execute(
            "INSERT INTO agent_mcp (agent_id, mcp_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
            agent_id, mcp_id,
        )

    async def detach(self, agent_id: UUID, mcp_id: UUID) -> None:
        await self._conn.execute(
            "DELETE FROM agent_mcp WHERE agent_id = $1 AND mcp_id = $2", agent_id, mcp_id
        )

    async def list_by_agent(self, agent_id: UUID) -> list[asyncpg.Record]:
        return await self._conn.fetch(
            "SELECT m.id, m.workspace_id, m.name, m.type, m.created_at FROM workspace_mcp m"
            " JOIN agent_mcp a ON a.mcp_id = m.id WHERE a.agent_id = $1",
            agent_id,
        )

    async def list_decrypted(self, agent_id: UUID) -> list[dict]:
        records = await self._conn.fetch(
            "SELECT m.name, m.config_encrypted FROM workspace_mcp m"
            " JOIN agent_mcp a ON a.mcp_id = m.id WHERE a.agent_id = $1",
            agent_id,
        )
        return [
            {"name": r["name"], "config": decrypt_json(bytes(r["config_encrypted"]))}
            for r in records
        ]
