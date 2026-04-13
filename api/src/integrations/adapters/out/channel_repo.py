from uuid import UUID

import asyncpg

from src.shared.crypto import decrypt_json, encrypt_json


class ChannelRepo:
    def __init__(self, conn: asyncpg.Pool) -> None:
        self._conn = conn

    async def create(self, user_id: UUID, name: str, type_: str, config: dict) -> asyncpg.Record:
        encrypted = encrypt_json(config)
        return await self._conn.fetchrow(
            "INSERT INTO user_channels (user_id, name, type, config_encrypted) VALUES ($1, $2, $3, $4) RETURNING *",
            user_id, name, type_, encrypted,
        )

    async def find_by_id(self, channel_id: UUID) -> asyncpg.Record | None:
        return await self._conn.fetchrow("SELECT * FROM user_channels WHERE id = $1", channel_id)

    async def list_by_user(self, user_id: UUID) -> list[asyncpg.Record]:
        return await self._conn.fetch(
            "SELECT id, user_id, name, type, created_at FROM user_channels WHERE user_id = $1", user_id
        )

    async def get_decrypted_config(self, channel_id: UUID) -> dict:
        record = await self.find_by_id(channel_id)
        if not record:
            raise ValueError(f"Channel {channel_id} not found")
        return decrypt_json(bytes(record["config_encrypted"]))

    async def delete(self, channel_id: UUID) -> None:
        await self._conn.execute("DELETE FROM user_channels WHERE id = $1", channel_id)
