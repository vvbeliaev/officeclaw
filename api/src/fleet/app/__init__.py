from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

import asyncpg

from src.fleet.app.agents import AgentService
from src.fleet.app.sandbox import SandboxService

if TYPE_CHECKING:
    from src.integrations.app import IntegrationsApp


class FleetApp:
    """Facade for the fleet domain — all fleet use-cases in one place."""

    def __init__(
        self,
        agents: AgentService,
        sandbox: SandboxService,
        integrations: IntegrationsApp,
    ) -> None:
        self._agents = agents
        self._sandbox = sandbox
        self._integrations = integrations

    # --- Agents ---

    async def create_agent(
        self, user_id: UUID, name: str, image: str, is_admin: bool = False
    ) -> asyncpg.Record:
        record = await self._agents.create(user_id, name, image, is_admin)
        # Auto-attach the user's default LLM provider so every new agent
        # has a working model out of the box. Skip for the Admin agent
        # (bootstrapped separately with its own env setup).
        if not is_admin:
            llm_env = await self._integrations.find_llm_provider(user_id)
            if llm_env:
                await self._integrations.attach_env(record["id"], llm_env["id"])
        return record

    async def find_agent(self, agent_id: UUID) -> asyncpg.Record | None:
        return await self._agents.find_by_id(agent_id)

    async def list_agents(self, user_id: UUID) -> list[asyncpg.Record]:
        return await self._agents.list_by_user(user_id)

    async def update_agent(
        self, agent_id: UUID, **fields: object
    ) -> asyncpg.Record | None:
        return await self._agents.update(agent_id, **fields)

    async def delete_agent(self, agent_id: UUID) -> None:
        await self._agents.delete(agent_id)

    # --- Files ---

    async def upsert_file(
        self, agent_id: UUID, path: str, content: str
    ) -> asyncpg.Record:
        return await self._agents.upsert_file(agent_id, path, content)

    async def find_file(self, agent_id: UUID, path: str) -> asyncpg.Record | None:
        return await self._agents.find_file(agent_id, path)

    async def list_files(self, agent_id: UUID) -> list[asyncpg.Record]:
        return await self._agents.list_files(agent_id)

    # --- Sandbox ---

    async def start_sandbox(self, agent_id: UUID) -> str:
        return await self._sandbox.start(agent_id)

    async def stop_sandbox(self, agent_id: UUID) -> None:
        await self._sandbox.stop(agent_id)

