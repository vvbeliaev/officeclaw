from uuid import UUID

import asyncpg

from src.integrations.adapters.out.repository import (
    AgentMcpRepo,
    ChannelRepo,
    EnvRepo,
    LinkRepo,
)


class IntegrationsService:
    def __init__(
        self,
        env_repo: EnvRepo,
        channel_repo: ChannelRepo,
        link_repo: LinkRepo,
        mcp_repo: AgentMcpRepo,
    ) -> None:
        self._envs = env_repo
        self._channels = channel_repo
        self._links = link_repo
        self._mcp = mcp_repo

    # --- Env ---

    async def create_env(self, user_id: UUID, name: str, values: dict) -> asyncpg.Record:
        return await self._envs.create(user_id, name, values)

    async def find_env(self, env_id: UUID) -> asyncpg.Record | None:
        return await self._envs.find_by_id(env_id)

    async def list_envs(self, user_id: UUID) -> list[asyncpg.Record]:
        return await self._envs.list_by_user(user_id)

    async def get_decrypted_env(self, env_id: UUID) -> dict:
        return await self._envs.get_decrypted_values(env_id)

    async def delete_env(self, env_id: UUID) -> None:
        await self._envs.delete(env_id)

    # --- Channel ---

    async def create_channel(self, user_id: UUID, type_: str, config: dict) -> asyncpg.Record:
        return await self._channels.create(user_id, type_, config)

    async def find_channel(self, channel_id: UUID) -> asyncpg.Record | None:
        return await self._channels.find_by_id(channel_id)

    async def list_channels(self, user_id: UUID) -> list[asyncpg.Record]:
        return await self._channels.list_by_user(user_id)

    async def get_decrypted_channel(self, channel_id: UUID) -> dict:
        return await self._channels.get_decrypted_config(channel_id)

    async def delete_channel(self, channel_id: UUID) -> None:
        await self._channels.delete(channel_id)

    # --- Links: skills ---

    async def attach_skill(self, agent_id: UUID, skill_id: UUID) -> None:
        await self._links.attach_skill(agent_id, skill_id)

    async def detach_skill(self, agent_id: UUID, skill_id: UUID) -> None:
        await self._links.detach_skill(agent_id, skill_id)

    async def list_agent_skills(self, agent_id: UUID) -> list[asyncpg.Record]:
        return await self._links.list_skills(agent_id)

    # --- Links: envs ---

    async def attach_env(self, agent_id: UUID, env_id: UUID) -> None:
        await self._links.attach_env(agent_id, env_id)

    async def detach_env(self, agent_id: UUID, env_id: UUID) -> None:
        await self._links.detach_env(agent_id, env_id)

    async def list_agent_envs(self, agent_id: UUID) -> list[asyncpg.Record]:
        return await self._links.list_envs(agent_id)

    # --- Links: channels ---

    async def attach_channel(self, agent_id: UUID, channel_id: UUID) -> None:
        await self._links.attach_channel(agent_id, channel_id)

    async def detach_channel(self, agent_id: UUID, channel_id: UUID) -> None:
        await self._links.detach_channel(agent_id, channel_id)

    async def list_agent_channels(self, agent_id: UUID) -> list[asyncpg.Record]:
        return await self._links.list_channels(agent_id)

    # --- MCP ---

    async def create_mcp(self, agent_id: UUID, name: str, config: dict) -> asyncpg.Record:
        return await self._mcp.create(agent_id, name, config)

    async def list_agent_mcp(self, agent_id: UUID) -> list[asyncpg.Record]:
        return await self._mcp.list_by_agent(agent_id)

    async def get_all_decrypted_mcp(self, agent_id: UUID) -> list[dict]:
        return await self._mcp.get_all_decrypted(agent_id)
