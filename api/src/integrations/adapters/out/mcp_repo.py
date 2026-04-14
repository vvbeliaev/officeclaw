from uuid import UUID

import asyncpg

from src.shared.crypto import decrypt_json, encrypt_json


class UserMcpRepo:
    def __init__(self, conn: asyncpg.Pool) -> None:
        self._conn = conn

    async def create(self, workspace_id: UUID, name: str, type_: str, config: dict) -> asyncpg.Record:
        encrypted = encrypt_json(config)
        return await self._conn.fetchrow(
            "INSERT INTO workspace_mcp (workspace_id, name, type, config_encrypted)"
            " VALUES ($1, $2, $3, $4) RETURNING id, workspace_id, name, type, created_at",
            workspace_id, name, type_, encrypted,
        )

    async def find_by_id(self, mcp_id: UUID) -> asyncpg.Record | None:
        return await self._conn.fetchrow(
            "SELECT id, workspace_id, name, type, created_at FROM workspace_mcp WHERE id = $1", mcp_id
        )

    async def list_by_workspace(self, workspace_id: UUID) -> list[asyncpg.Record]:
        return await self._conn.fetch(
            "SELECT id, workspace_id, name, type, created_at FROM workspace_mcp WHERE workspace_id = $1"
            " ORDER BY created_at DESC",
            workspace_id,
        )

    async def get_decrypted_config(self, mcp_id: UUID) -> dict:
        record = await self._conn.fetchrow(
            "SELECT config_encrypted FROM workspace_mcp WHERE id = $1", mcp_id
        )
        if not record:
            raise ValueError(f"MCP {mcp_id} not found")
        return decrypt_json(bytes(record["config_encrypted"]))

    async def delete(self, mcp_id: UUID) -> None:
        await self._conn.execute("DELETE FROM workspace_mcp WHERE id = $1", mcp_id)
