from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

import asyncpg

from src.fleet.app.agents import AgentService
from src.fleet.app.sandbox import SandboxService

if TYPE_CHECKING:
    from src.integrations.app import IntegrationsApp


class FleetApp:
    def __init__(
        self,
        agents: AgentService,
        sandbox: SandboxService,
        integrations: IntegrationsApp,
    ) -> None:
        self._agents = agents
        self._sandbox = sandbox
        self._integrations = integrations

    async def create_agent(
        self, workspace_id: UUID, name: str, image: str, is_admin: bool = False
    ) -> asyncpg.Record:
        record = await self._agents.create(workspace_id, name, image, is_admin)
        if not is_admin:
            llm_env = await self._integrations.find_llm_provider(workspace_id)
            if llm_env:
                await self._integrations.attach_env(record["id"], llm_env["id"])
        return record

    async def find_agent(self, agent_id: UUID) -> asyncpg.Record | None:
        return await self._agents.find_by_id(agent_id)

    async def list_agents(self, workspace_id: UUID) -> list[asyncpg.Record]:
        return await self._agents.list_by_workspace(workspace_id)

    async def update_agent(self, agent_id: UUID, **fields: object) -> asyncpg.Record | None:
        return await self._agents.update(agent_id, **fields)

    async def delete_agent(self, agent_id: UUID) -> None:
        await self._agents.delete(agent_id)

    async def upsert_file(self, agent_id: UUID, path: str, content: str) -> asyncpg.Record:
        return await self._agents.upsert_file(agent_id, path, content)

    async def find_file(self, agent_id: UUID, path: str) -> asyncpg.Record | None:
        return await self._agents.find_file(agent_id, path)

    async def list_files(self, agent_id: UUID) -> list[asyncpg.Record]:
        return await self._agents.list_files(agent_id)

    async def start_sandbox(self, agent_id: UUID, workspace_token: str) -> str:
        return await self._sandbox.start(agent_id, workspace_token)

    async def stop_sandbox(self, agent_id: UUID) -> None:
        await self._sandbox.stop(agent_id)
