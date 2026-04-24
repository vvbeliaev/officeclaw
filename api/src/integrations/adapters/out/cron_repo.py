from uuid import UUID

import asyncpg


_CRON_COLS = (
    "id, workspace_id, name,"
    " schedule_kind, schedule_at_ms, schedule_every_ms, schedule_expr, schedule_tz,"
    " message, deliver, channel, recipient, delete_after_run,"
    " created_at, updated_at"
)


class WorkspaceCronRepo:
    def __init__(self, conn: asyncpg.Pool) -> None:
        self._conn = conn

    async def create(
        self,
        workspace_id: UUID,
        name: str,
        schedule_kind: str,
        schedule_at_ms: int | None,
        schedule_every_ms: int | None,
        schedule_expr: str | None,
        schedule_tz: str | None,
        message: str,
        deliver: bool,
        channel: str | None,
        recipient: str | None,
        delete_after_run: bool,
    ) -> asyncpg.Record:
        return await self._conn.fetchrow(
            f"INSERT INTO workspace_crons"
            " (workspace_id, name, schedule_kind, schedule_at_ms, schedule_every_ms,"
            "  schedule_expr, schedule_tz, message, deliver, channel, recipient, delete_after_run)"
            " VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)"
            f" RETURNING {_CRON_COLS}",
            workspace_id, name, schedule_kind, schedule_at_ms, schedule_every_ms,
            schedule_expr, schedule_tz, message, deliver, channel, recipient, delete_after_run,
        )

    async def find_by_id(self, cron_id: UUID) -> asyncpg.Record | None:
        return await self._conn.fetchrow(
            f"SELECT {_CRON_COLS} FROM workspace_crons WHERE id = $1", cron_id
        )

    async def list_by_workspace(self, workspace_id: UUID) -> list[asyncpg.Record]:
        return await self._conn.fetch(
            f"SELECT {_CRON_COLS} FROM workspace_crons WHERE workspace_id = $1"
            " ORDER BY created_at ASC",
            workspace_id,
        )

    async def update(self, cron_id: UUID, **fields) -> asyncpg.Record | None:
        allowed = {
            "name", "schedule_kind", "schedule_at_ms", "schedule_every_ms",
            "schedule_expr", "schedule_tz", "message", "deliver",
            "channel", "recipient", "delete_after_run",
        }
        unknown = set(fields) - allowed
        if unknown:
            raise ValueError(f"Unknown cron fields: {unknown}")
        if not fields:
            return await self.find_by_id(cron_id)
        set_clauses = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(fields))
        values = list(fields.values())
        return await self._conn.fetchrow(
            f"UPDATE workspace_crons SET {set_clauses}, updated_at = NOW()"
            f" WHERE id = $1 RETURNING {_CRON_COLS}",
            cron_id, *values,
        )

    async def delete(self, cron_id: UUID) -> None:
        await self._conn.execute("DELETE FROM workspace_crons WHERE id = $1", cron_id)
