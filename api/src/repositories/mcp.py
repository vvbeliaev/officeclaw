from uuid import UUID
import asyncpg
from src.crypto import encrypt_json, decrypt_json


class AgentMcpRepo:
    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def create(self, agent_id: UUID, name: str, config: dict) -> asyncpg.Record:
        return await self._conn.fetchrow(
            "INSERT INTO agent_mcp (agent_id, name, config_encrypted) VALUES ($1, $2, $3) RETURNING id, agent_id, name",
            agent_id, name, encrypt_json(config),
        )

    async def list_by_agent(self, agent_id: UUID) -> list[asyncpg.Record]:
        return await self._conn.fetch(
            "SELECT id, agent_id, name FROM agent_mcp WHERE agent_id = $1", agent_id
        )

    async def get_all_decrypted(self, agent_id: UUID) -> list[dict]:
        records = await self._conn.fetch(
            "SELECT name, config_encrypted FROM agent_mcp WHERE agent_id = $1", agent_id
        )
        return [
            {"name": r["name"], "config": decrypt_json(bytes(r["config_encrypted"]))}
            for r in records
        ]

    async def delete(self, mcp_id: UUID) -> None:
        await self._conn.execute("DELETE FROM agent_mcp WHERE id = $1", mcp_id)
