from uuid import UUID
import asyncpg


class UserRepo:
    def __init__(self, conn: asyncpg.Pool) -> None:
        self._conn = conn

    async def create(self, email: str) -> asyncpg.Record:
        return await self._conn.fetchrow(
            "INSERT INTO users (email) VALUES ($1) RETURNING *", email
        )

    async def find_by_id(self, user_id: UUID) -> asyncpg.Record | None:
        return await self._conn.fetchrow(
            "SELECT * FROM users WHERE id = $1", user_id
        )

    async def find_by_email(self, email: str) -> asyncpg.Record | None:
        return await self._conn.fetchrow(
            "SELECT * FROM users WHERE email = $1", email
        )

    async def set_token(self, user_id: UUID, token: str) -> None:
        await self._conn.execute(
            "UPDATE users SET officeclaw_token = $2 WHERE id = $1",
            user_id, token,
        )

    async def find_by_token(self, token: str) -> asyncpg.Record | None:
        return await self._conn.fetchrow(
            "SELECT id FROM users WHERE officeclaw_token = $1", token
        )
