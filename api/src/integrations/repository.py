from uuid import UUID
import asyncpg
from src.shared.crypto import encrypt_json, decrypt_json


class EnvRepo:
    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def create(self, user_id: UUID, name: str, values: dict) -> asyncpg.Record:
        encrypted = encrypt_json(values)
        return await self._conn.fetchrow(
            "INSERT INTO user_envs (user_id, name, values_encrypted) VALUES ($1, $2, $3) RETURNING *",
            user_id, name, encrypted,
        )

    async def find_by_id(self, env_id: UUID) -> asyncpg.Record | None:
        return await self._conn.fetchrow("SELECT * FROM user_envs WHERE id = $1", env_id)

    async def list_by_user(self, user_id: UUID) -> list[asyncpg.Record]:
        return await self._conn.fetch(
            "SELECT id, user_id, name, created_at FROM user_envs WHERE user_id = $1", user_id
        )

    async def get_decrypted_values(self, env_id: UUID) -> dict:
        record = await self.find_by_id(env_id)
        if not record:
            raise ValueError(f"Env {env_id} not found")
        return decrypt_json(bytes(record["values_encrypted"]))

    async def delete(self, env_id: UUID) -> None:
        await self._conn.execute("DELETE FROM user_envs WHERE id = $1", env_id)


class ChannelRepo:
    def __init__(self, conn: asyncpg.Connection) -> None:
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
            "SELECT e.id, e.user_id, e.name, e.created_at FROM user_envs e JOIN agent_envs a ON a.env_id = e.id WHERE a.agent_id = $1",
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
            "SELECT c.id, c.user_id, c.type, c.created_at FROM user_channels c JOIN agent_channels a ON a.channel_id = c.id WHERE a.agent_id = $1",
            agent_id,
        )


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

    async def get_decrypted_config(self, mcp_id: UUID) -> dict:
        record = await self._conn.fetchrow(
            "SELECT config_encrypted FROM agent_mcp WHERE id = $1", mcp_id
        )
        if not record:
            raise ValueError(f"MCP {mcp_id} not found")
        return decrypt_json(bytes(record["config_encrypted"]))

    async def delete(self, mcp_id: UUID) -> None:
        await self._conn.execute("DELETE FROM agent_mcp WHERE id = $1", mcp_id)
