from uuid import UUID

import asyncpg

from src.shared.crypto import decrypt_json, encrypt_json


class EnvRepo:
    def __init__(self, conn: asyncpg.Pool) -> None:
        self._conn = conn

    async def create(self, workspace_id: UUID, name: str, values: dict, category: str | None = None) -> asyncpg.Record:
        encrypted = encrypt_json(values)
        return await self._conn.fetchrow(
            "INSERT INTO workspace_envs (workspace_id, name, values_encrypted, category)"
            " VALUES ($1, $2, $3, $4)"
            " RETURNING id, workspace_id, name, category, created_at",
            workspace_id, name, encrypted, category,
        )

    async def find_by_id(self, env_id: UUID) -> asyncpg.Record | None:
        return await self._conn.fetchrow(
            "SELECT id, workspace_id, name, category, created_at FROM workspace_envs WHERE id = $1", env_id
        )

    async def list_by_workspace(self, workspace_id: UUID) -> list[asyncpg.Record]:
        return await self._conn.fetch(
            "SELECT id, workspace_id, name, category, created_at FROM workspace_envs WHERE workspace_id = $1", workspace_id
        )

    async def find_llm_provider_by_workspace(self, workspace_id: UUID) -> asyncpg.Record | None:
        """Return the first llm-provider env for the workspace (prefers 'default-llm')."""
        return await self._conn.fetchrow(
            "SELECT id, workspace_id, name, category, created_at FROM workspace_envs"
            " WHERE workspace_id = $1 AND category = 'llm-provider'"
            " ORDER BY (name = 'default-llm') DESC, created_at ASC"
            " LIMIT 1",
            workspace_id,
        )

    async def find_web_search_by_workspace(self, workspace_id: UUID) -> asyncpg.Record | None:
        """Return the first web-search env for the workspace (prefers 'default-web-search')."""
        return await self._conn.fetchrow(
            "SELECT id, workspace_id, name, category, created_at FROM workspace_envs"
            " WHERE workspace_id = $1 AND category = 'web-search'"
            " ORDER BY (name = 'default-web-search') DESC, created_at ASC"
            " LIMIT 1",
            workspace_id,
        )

    async def get_decrypted_values(self, env_id: UUID) -> dict:
        record = await self._conn.fetchrow(
            "SELECT values_encrypted FROM workspace_envs WHERE id = $1", env_id
        )
        if not record:
            raise ValueError(f"Env {env_id} not found")
        return decrypt_json(bytes(record["values_encrypted"]))

    async def update(
        self, env_id: UUID, name: str | None = None, values: dict | None = None, category: str | None = None
    ) -> asyncpg.Record | None:
        parts: list[str] = []
        params: list = [env_id]
        i = 2

        if name is not None:
            parts.append(f"name = ${i}")
            params.append(name)
            i += 1

        if values is not None:
            parts.append(f"values_encrypted = ${i}")
            params.append(encrypt_json(values))
            i += 1

        if category is not None:
            parts.append(f"category = ${i}")
            params.append(category)
            i += 1

        if not parts:
            return await self.find_by_id(env_id)

        return await self._conn.fetchrow(
            f"UPDATE workspace_envs SET {', '.join(parts)} WHERE id = $1"
            " RETURNING id, workspace_id, name, category, created_at",
            *params,
        )

    async def delete(self, env_id: UUID) -> None:
        await self._conn.execute("DELETE FROM workspace_envs WHERE id = $1", env_id)
