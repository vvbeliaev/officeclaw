from uuid import UUID
import asyncpg


class UserRepo:
    def __init__(self, conn: asyncpg.Pool) -> None:
        self._conn = conn

    async def create(self, email: str) -> asyncpg.Record:
        return await self._conn.fetchrow(
            'INSERT INTO "user" (email) VALUES ($1) RETURNING *', email
        )

    async def find_by_id(self, user_id: UUID) -> asyncpg.Record | None:
        return await self._conn.fetchrow(
            'SELECT * FROM "user" WHERE id = $1', user_id
        )

    async def find_by_email(self, email: str) -> asyncpg.Record | None:
        return await self._conn.fetchrow(
            'SELECT * FROM "user" WHERE email = $1', email
        )
