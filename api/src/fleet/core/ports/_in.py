"""Primary (inbound) ports — interfaces that in-adapters call into the app layer."""
from typing import Protocol
from uuid import UUID


class ISandboxService(Protocol):
    async def start(self, agent_id: UUID) -> str: ...
    async def stop(self, agent_id: UUID) -> None: ...
