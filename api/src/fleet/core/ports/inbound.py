"""Primary (inbound) ports — interfaces that in-adapters call into the app layer."""
from typing import Protocol
from uuid import UUID

import asyncpg


class IStartSandbox(Protocol):
    async def __call__(self, conn: asyncpg.Connection, agent_id: UUID) -> str: ...


class IStopSandbox(Protocol):
    async def __call__(self, conn: asyncpg.Connection, agent_id: UUID) -> None: ...
