import json
from uuid import UUID

import asyncpg


_AGENT_CRON_JOIN_COLS = (
    "c.id, c.workspace_id, c.name,"
    " c.schedule_kind, c.schedule_at_ms, c.schedule_every_ms, c.schedule_expr, c.schedule_tz,"
    " c.message, c.deliver, c.channel, c.recipient, c.delete_after_run,"
    " c.created_at, c.updated_at,"
    " ac.enabled, ac.next_run_at_ms, ac.last_run_at_ms, ac.last_status, ac.last_error,"
    " ac.run_history"
)


def _row_to_dict(rec: asyncpg.Record) -> dict:
    d = dict(rec)
    history = d.get("run_history")
    if isinstance(history, str):
        try:
            d["run_history"] = json.loads(history)
        except (TypeError, ValueError):
            d["run_history"] = []
    return d


class CronLinkRepo:
    def __init__(self, conn: asyncpg.Pool) -> None:
        self._conn = conn

    async def attach(self, agent_id: UUID, cron_id: UUID, enabled: bool = True) -> None:
        await self._conn.execute(
            "INSERT INTO agent_crons (agent_id, cron_id, enabled) VALUES ($1,$2,$3)"
            " ON CONFLICT (agent_id, cron_id) DO UPDATE SET enabled = EXCLUDED.enabled",
            agent_id, cron_id, enabled,
        )

    async def detach(self, agent_id: UUID, cron_id: UUID) -> None:
        await self._conn.execute(
            "DELETE FROM agent_crons WHERE agent_id = $1 AND cron_id = $2",
            agent_id, cron_id,
        )

    async def set_enabled(self, agent_id: UUID, cron_id: UUID, enabled: bool) -> asyncpg.Record | None:
        return await self._conn.fetchrow(
            "UPDATE agent_crons SET enabled = $3"
            " WHERE agent_id = $1 AND cron_id = $2"
            " RETURNING agent_id, cron_id, enabled, next_run_at_ms, last_run_at_ms,"
            " last_status, last_error, run_history",
            agent_id, cron_id, enabled,
        )

    async def list_by_agent(self, agent_id: UUID) -> list[dict]:
        rows = await self._conn.fetch(
            f"SELECT {_AGENT_CRON_JOIN_COLS} FROM workspace_crons c"
            " JOIN agent_crons ac ON ac.cron_id = c.id"
            " WHERE ac.agent_id = $1"
            " ORDER BY c.created_at ASC",
            agent_id,
        )
        return [_row_to_dict(r) for r in rows]
