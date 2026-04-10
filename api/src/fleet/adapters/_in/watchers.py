import asyncio
import logging

from src.fleet.app.sandbox import SandboxService

_log = logging.getLogger(__name__)
_HEALTH_CHECK_INTERVAL = 30  # seconds between liveness checks
_FILE_SYNC_INTERVAL = 300  # seconds between workspace file syncs (5 min)


class SandboxWatcher:
    """Inbound adapter: drives sandbox health-check and file-sync loops."""

    def __init__(self, sandbox: SandboxService) -> None:
        self._sandbox = sandbox
        self._tasks: list[asyncio.Task] = []

    def start(self) -> None:
        self._tasks = [
            asyncio.create_task(self._health_check_loop(), name="health_check"),
            asyncio.create_task(self._sync_loop(), name="file_sync"),
        ]

    async def stop(self) -> None:
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks = []

    async def _health_check_loop(self) -> None:
        while True:
            try:
                await self._sandbox.check_health()
            except Exception:
                _log.exception("Health check loop error")
            await asyncio.sleep(_HEALTH_CHECK_INTERVAL)

    async def _sync_loop(self) -> None:
        await asyncio.sleep(_FILE_SYNC_INTERVAL)  # stagger first run from health check
        while True:
            try:
                await self._sandbox.sync_all()
            except Exception:
                _log.exception("File sync loop error")
            await asyncio.sleep(_FILE_SYNC_INTERVAL)
