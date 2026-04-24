from uuid import UUID

import asyncpg

from src.integrations.adapters.out.cron_repo import WorkspaceCronRepo


class CronService:
    def __init__(self, repo: WorkspaceCronRepo) -> None:
        self._repo = repo

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
        return await self._repo.create(
            workspace_id, name, schedule_kind, schedule_at_ms, schedule_every_ms,
            schedule_expr, schedule_tz, message, deliver, channel, recipient, delete_after_run,
        )

    async def find(self, cron_id: UUID) -> asyncpg.Record | None:
        return await self._repo.find_by_id(cron_id)

    async def list(self, workspace_id: UUID) -> list[asyncpg.Record]:
        return await self._repo.list_by_workspace(workspace_id)

    async def update(self, cron_id: UUID, **fields) -> asyncpg.Record | None:
        return await self._repo.update(cron_id, **fields)

    async def delete(self, cron_id: UUID) -> None:
        await self._repo.delete(cron_id)
