from uuid import UUID

import asyncpg

from src.integrations.adapters.out.repository import (
    ChannelRepo,
    EnvRepo,
    LinkRepo,
    UserMcpRepo,
    UserTemplateRepo,
)


class IntegrationsService:
    def __init__(
        self,
        env_repo: EnvRepo,
        channel_repo: ChannelRepo,
        link_repo: LinkRepo,
        mcp_repo: UserMcpRepo,
        template_repo: UserTemplateRepo,
    ) -> None:
        self._envs = env_repo
        self._channels = channel_repo
        self._links = link_repo
        self._mcp = mcp_repo
        self._templates = template_repo

    # --- Env ---

    async def create_env(self, user_id: UUID, name: str, values: dict, category: str | None = None) -> asyncpg.Record:
        return await self._envs.create(user_id, name, values, category)

    async def find_env(self, env_id: UUID) -> asyncpg.Record | None:
        return await self._envs.find_by_id(env_id)

    async def list_envs(self, user_id: UUID) -> list[asyncpg.Record]:
        return await self._envs.list_by_user(user_id)

    async def get_decrypted_env(self, env_id: UUID) -> dict:
        return await self._envs.get_decrypted_values(env_id)

    async def update_env(
        self, env_id: UUID, name: str | None = None, values: dict | None = None, category: str | None = None
    ) -> asyncpg.Record | None:
        return await self._envs.update(env_id, name=name, values=values, category=category)

    async def delete_env(self, env_id: UUID) -> None:
        await self._envs.delete(env_id)

    async def find_llm_provider(self, user_id: UUID) -> asyncpg.Record | None:
        return await self._envs.find_llm_provider_by_user(user_id)

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

    # --- MCP ---

    async def create_mcp(self, user_id: UUID, name: str, type_: str, config: dict) -> asyncpg.Record:
        return await self._mcp.create(user_id, name, type_, config)

    async def find_mcp(self, mcp_id: UUID) -> asyncpg.Record | None:
        return await self._mcp.find_by_id(mcp_id)

    async def list_mcps(self, user_id: UUID) -> list[asyncpg.Record]:
        return await self._mcp.list_by_user(user_id)

    async def delete_mcp(self, mcp_id: UUID) -> None:
        await self._mcp.delete(mcp_id)

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

    # --- Links: mcp ---

    async def attach_mcp(self, agent_id: UUID, mcp_id: UUID) -> None:
        await self._links.attach_mcp(agent_id, mcp_id)

    async def detach_mcp(self, agent_id: UUID, mcp_id: UUID) -> None:
        await self._links.detach_mcp(agent_id, mcp_id)

    async def list_agent_mcps(self, agent_id: UUID) -> list[asyncpg.Record]:
        return await self._links.list_mcps(agent_id)

    async def get_all_decrypted_mcp(self, agent_id: UUID) -> list[dict]:
        return await self._links.list_mcps_decrypted(agent_id)

    # --- Templates ---

    async def create_template(
        self, user_id: UUID, name: str, template_type: str, content: str
    ) -> asyncpg.Record:
        return await self._templates.create(user_id, name, template_type, content)

    async def find_template(self, template_id: UUID) -> asyncpg.Record | None:
        return await self._templates.find_by_id(template_id)

    async def list_templates(self, user_id: UUID) -> list[asyncpg.Record]:
        return await self._templates.list_by_user(user_id)

    async def update_template(
        self, template_id: UUID, name: str | None = None, content: str | None = None
    ) -> asyncpg.Record | None:
        return await self._templates.update(template_id, name=name, content=content)

    async def delete_template(self, template_id: UUID) -> None:
        await self._templates.delete(template_id)

    # --- Links: templates ---

    async def attach_template(
        self, agent_id: UUID, template_id: UUID, template_type: str
    ) -> None:
        await self._links.attach_template(agent_id, template_id, template_type)

    async def detach_template(self, agent_id: UUID, template_id: UUID) -> None:
        await self._links.detach_template(agent_id, template_id)

    async def list_agent_templates(self, agent_id: UUID) -> list[asyncpg.Record]:
        return await self._links.list_templates(agent_id)
