from uuid import UUID
import asyncpg
from src.crypto import encrypt_json, decrypt_json


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
