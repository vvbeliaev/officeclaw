# api/src/library/repository.py
import json
from typing import Any
from uuid import UUID

import asyncpg


def _row_to_dict(record: asyncpg.Record | None) -> dict | None:
    """Convert a skills row to a plain dict, decoding metadata_extra JSONB along the way."""
    if record is None:
        return None
    data = dict(record)
    metadata_extra = data.get("metadata_extra")
    if isinstance(metadata_extra, str):
        try:
            data["metadata_extra"] = json.loads(metadata_extra)
        except (TypeError, ValueError):
            data["metadata_extra"] = {}
    elif metadata_extra is None:
        data["metadata_extra"] = {}
    return data


class SkillRepo:
    def __init__(self, conn: asyncpg.Pool) -> None:
        self._conn = conn

    async def create(
        self,
        workspace_id: UUID,
        name: str,
        description: str,
        *,
        always: bool = False,
        emoji: str | None = None,
        homepage: str | None = None,
        required_bins: list[str] | None = None,
        required_envs: list[str] | None = None,
        metadata_extra: dict[str, Any] | None = None,
    ) -> dict:
        record = await self._conn.fetchrow(
            """
            INSERT INTO skills
                (workspace_id, name, description, always, emoji, homepage,
                 required_bins, required_envs, metadata_extra)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb)
            RETURNING *
            """,
            workspace_id,
            name,
            description,
            always,
            emoji,
            homepage,
            required_bins or [],
            required_envs or [],
            json.dumps(metadata_extra or {}),
        )
        return _row_to_dict(record)

    async def find_by_id(self, skill_id: UUID) -> dict | None:
        return _row_to_dict(
            await self._conn.fetchrow("SELECT * FROM skills WHERE id = $1", skill_id)
        )

    async def list_by_workspace(self, workspace_id: UUID) -> list[dict]:
        records = await self._conn.fetch(
            "SELECT * FROM skills WHERE workspace_id = $1", workspace_id
        )
        return [_row_to_dict(r) for r in records]

    async def delete(self, skill_id: UUID) -> None:
        await self._conn.execute("DELETE FROM skills WHERE id = $1", skill_id)

    # Column → optional SQL cast used when parameterizing non-scalar values.
    _UPDATABLE: dict[str, str] = {
        "name": "",
        "description": "",
        "always": "",
        "emoji": "",
        "homepage": "",
        "required_bins": "",
        "required_envs": "",
        "metadata_extra": "::jsonb",
    }

    async def update(self, skill_id: UUID, **fields: Any) -> dict | None:
        """Update whichever columns are present in `fields`.

        Presence — not truthiness — is what decides whether a column is
        written. This is what lets the caller explicitly null out
        `emoji`/`homepage` via PATCH with `{"emoji": null}`.
        Unknown keys are silently dropped so stray form fields from a
        client cannot target columns we don't intend to expose.
        """
        sets: list[str] = []
        values: list[object] = []
        for col, cast in self._UPDATABLE.items():
            if col not in fields:
                continue
            value: Any = fields[col]
            # metadata_extra arrives as a dict; asyncpg wants a JSON string
            # with an explicit ::jsonb cast on the placeholder.
            if col == "metadata_extra" and value is not None:
                value = json.dumps(value)
            placeholder = f"${len(values) + 1}{cast}"
            sets.append(f"{col} = {placeholder}")
            values.append(value)

        if not sets:
            return await self.find_by_id(skill_id)
        values.append(skill_id)
        query = (
            f"UPDATE skills SET {', '.join(sets)} WHERE id = ${len(values)} RETURNING *"
        )
        return _row_to_dict(await self._conn.fetchrow(query, *values))


class SkillFileRepo:
    def __init__(self, conn: asyncpg.Pool) -> None:
        self._conn = conn

    async def upsert(self, skill_id: UUID, path: str, content: str) -> asyncpg.Record:
        return await self._conn.fetchrow(
            """INSERT INTO skill_files (skill_id, path, content) VALUES ($1, $2, $3)
               ON CONFLICT (skill_id, path)
               DO UPDATE SET content = EXCLUDED.content, updated_at = NOW()
               RETURNING *""",
            skill_id,
            path,
            content,
        )

    async def list_by_skill(self, skill_id: UUID) -> list[asyncpg.Record]:
        return await self._conn.fetch(
            "SELECT * FROM skill_files WHERE skill_id = $1 ORDER BY path", skill_id
        )

    async def delete(self, skill_id: UUID, path: str) -> bool:
        result = await self._conn.execute(
            "DELETE FROM skill_files WHERE skill_id = $1 AND path = $2",
            skill_id,
            path,
        )
        return result.endswith(" 1")
