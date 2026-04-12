from uuid import UUID

import asyncpg


class UserTemplateRepo:
    def __init__(self, conn: asyncpg.Pool) -> None:
        self._conn = conn

    async def create(self, user_id: UUID, name: str, template_type: str, content: str) -> asyncpg.Record:
        return await self._conn.fetchrow(
            "INSERT INTO user_templates (user_id, name, template_type, content)"
            " VALUES ($1, $2, $3, $4)"
            " RETURNING id, user_id, name, template_type, content, created_at, updated_at",
            user_id, name, template_type, content,
        )

    async def find_by_id(self, template_id: UUID) -> asyncpg.Record | None:
        return await self._conn.fetchrow(
            "SELECT id, user_id, name, template_type, content, created_at, updated_at"
            " FROM user_templates WHERE id = $1",
            template_id,
        )

    async def list_by_user(self, user_id: UUID) -> list[asyncpg.Record]:
        return await self._conn.fetch(
            "SELECT id, user_id, name, template_type, content, created_at, updated_at"
            " FROM user_templates WHERE user_id = $1 ORDER BY created_at DESC",
            user_id,
        )

    async def update(
        self, template_id: UUID, name: str | None = None, content: str | None = None
    ) -> asyncpg.Record | None:
        parts: list[str] = ["updated_at = now()"]
        params: list = [template_id]
        i = 2
        if name is not None:
            parts.append(f"name = ${i}")
            params.append(name)
            i += 1
        if content is not None:
            parts.append(f"content = ${i}")
            params.append(content)
            i += 1
        return await self._conn.fetchrow(
            f"UPDATE user_templates SET {', '.join(parts)} WHERE id = $1"
            " RETURNING id, user_id, name, template_type, content, created_at, updated_at",
            *params,
        )

    async def delete(self, template_id: UUID) -> None:
        await self._conn.execute("DELETE FROM user_templates WHERE id = $1", template_id)
