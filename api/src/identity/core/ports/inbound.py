"""Primary (inbound) ports — interfaces that in-adapters call into the app layer."""
from typing import Protocol
from uuid import UUID

import asyncpg


class ICreateAdmin(Protocol):
    async def __call__(self, conn: asyncpg.Connection, user_id: UUID) -> None: ...
