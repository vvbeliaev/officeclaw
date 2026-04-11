from uuid import UUID
import asyncpg
from src.shared.crypto import encrypt_json, decrypt_json


class EnvRepo:
    def __init__(self, conn: asyncpg.Pool) -> None:
        self._conn = conn

    async def create(self, user_id: UUID, name: str, values: dict, category: str | None = None) -> asyncpg.Record:
        encrypted = encrypt_json(values)
        return await self._conn.fetchrow(
            "INSERT INTO user_envs (user_id, name, values_encrypted, category)"
            " VALUES ($1, $2, $3, $4)"
            " RETURNING id, user_id, name, category, created_at",
            user_id, name, encrypted, category,
        )

    async def find_by_id(self, env_id: UUID) -> asyncpg.Record | None:
        return await self._conn.fetchrow(
            "SELECT id, user_id, name, category, created_at FROM user_envs WHERE id = $1", env_id
        )

    async def list_by_user(self, user_id: UUID) -> list[asyncpg.Record]:
        return await self._conn.fetch(
            "SELECT id, user_id, name, category, created_at FROM user_envs WHERE user_id = $1", user_id
        )

    async def get_decrypted_values(self, env_id: UUID) -> dict:
        record = await self._conn.fetchrow(
            "SELECT values_encrypted FROM user_envs WHERE id = $1", env_id
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
            f"UPDATE user_envs SET {', '.join(parts)} WHERE id = $1"
            " RETURNING id, user_id, name, category, created_at",
            *params,
        )

    async def delete(self, env_id: UUID) -> None:
        await self._conn.execute("DELETE FROM user_envs WHERE id = $1", env_id)


class ChannelRepo:
    def __init__(self, conn: asyncpg.Pool) -> None:
        self._conn = conn

    async def create(self, user_id: UUID, type_: str, config: dict) -> asyncpg.Record:
        encrypted = encrypt_json(config)
        return await self._conn.fetchrow(
            "INSERT INTO user_channels (user_id, type, config_encrypted) VALUES ($1, $2, $3) RETURNING *",
            user_id, type_, encrypted,
        )

    async def find_by_id(self, channel_id: UUID) -> asyncpg.Record | None:
        return await self._conn.fetchrow("SELECT * FROM user_channels WHERE id = $1", channel_id)

    async def list_by_user(self, user_id: UUID) -> list[asyncpg.Record]:
        return await self._conn.fetch(
            "SELECT id, user_id, type, created_at FROM user_channels WHERE user_id = $1", user_id
        )

    async def get_decrypted_config(self, channel_id: UUID) -> dict:
        record = await self.find_by_id(channel_id)
        if not record:
            raise ValueError(f"Channel {channel_id} not found")
        return decrypt_json(bytes(record["config_encrypted"]))

    async def delete(self, channel_id: UUID) -> None:
        await self._conn.execute("DELETE FROM user_channels WHERE id = $1", channel_id)


class UserMcpRepo:
    def __init__(self, conn: asyncpg.Pool) -> None:
        self._conn = conn

    async def create(self, user_id: UUID, name: str, type_: str, config: dict) -> asyncpg.Record:
        encrypted = encrypt_json(config)
        return await self._conn.fetchrow(
            "INSERT INTO user_mcp (user_id, name, type, config_encrypted)"
            " VALUES ($1, $2, $3, $4) RETURNING id, user_id, name, type, created_at",
            user_id, name, type_, encrypted,
        )

    async def find_by_id(self, mcp_id: UUID) -> asyncpg.Record | None:
        return await self._conn.fetchrow(
            "SELECT id, user_id, name, type, created_at FROM user_mcp WHERE id = $1", mcp_id
        )

    async def list_by_user(self, user_id: UUID) -> list[asyncpg.Record]:
        return await self._conn.fetch(
            "SELECT id, user_id, name, type, created_at FROM user_mcp WHERE user_id = $1"
            " ORDER BY created_at DESC",
            user_id,
        )

    async def get_decrypted_config(self, mcp_id: UUID) -> dict:
        record = await self._conn.fetchrow(
            "SELECT config_encrypted FROM user_mcp WHERE id = $1", mcp_id
        )
        if not record:
            raise ValueError(f"MCP {mcp_id} not found")
        return decrypt_json(bytes(record["config_encrypted"]))

    async def delete(self, mcp_id: UUID) -> None:
        await self._conn.execute("DELETE FROM user_mcp WHERE id = $1", mcp_id)


class LinkRepo:
    def __init__(self, conn: asyncpg.Pool) -> None:
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
            "SELECT e.id, e.user_id, e.name, e.created_at FROM user_envs e"
            " JOIN agent_envs a ON a.env_id = e.id WHERE a.agent_id = $1",
            agent_id,
        )

    async def attach_channel(self, agent_id: UUID, channel_id: UUID) -> None:
        # ON CONFLICT ON CONSTRAINT covers only the PK (same agent re-attaching same channel
        # is idempotent). A unique violation on channel_id alone (different agent) propagates.
        await self._conn.execute(
            "INSERT INTO agent_channels (agent_id, channel_id) VALUES ($1, $2)"
            " ON CONFLICT ON CONSTRAINT agent_channels_pkey DO NOTHING",
            agent_id, channel_id,
        )

    async def detach_channel(self, agent_id: UUID, channel_id: UUID) -> None:
        await self._conn.execute(
            "DELETE FROM agent_channels WHERE agent_id = $1 AND channel_id = $2", agent_id, channel_id
        )

    async def list_channels(self, agent_id: UUID) -> list[asyncpg.Record]:
        return await self._conn.fetch(
            "SELECT c.id, c.user_id, c.type, c.created_at FROM user_channels c"
            " JOIN agent_channels a ON a.channel_id = c.id WHERE a.agent_id = $1",
            agent_id,
        )

    async def attach_mcp(self, agent_id: UUID, mcp_id: UUID) -> None:
        await self._conn.execute(
            "INSERT INTO agent_mcp (agent_id, mcp_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
            agent_id, mcp_id,
        )

    async def detach_mcp(self, agent_id: UUID, mcp_id: UUID) -> None:
        await self._conn.execute(
            "DELETE FROM agent_mcp WHERE agent_id = $1 AND mcp_id = $2", agent_id, mcp_id
        )

    async def list_mcps(self, agent_id: UUID) -> list[asyncpg.Record]:
        return await self._conn.fetch(
            "SELECT m.id, m.user_id, m.name, m.type, m.created_at FROM user_mcp m"
            " JOIN agent_mcp a ON a.mcp_id = m.id WHERE a.agent_id = $1",
            agent_id,
        )

    async def list_mcps_decrypted(self, agent_id: UUID) -> list[dict]:
        records = await self._conn.fetch(
            "SELECT m.name, m.config_encrypted FROM user_mcp m"
            " JOIN agent_mcp a ON a.mcp_id = m.id WHERE a.agent_id = $1",
            agent_id,
        )
        return [
            {"name": r["name"], "config": decrypt_json(bytes(r["config_encrypted"]))}
            for r in records
        ]
