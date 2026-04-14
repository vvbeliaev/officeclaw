from uuid import UUID

import asyncpg

from src.integrations.app.channel_service import ChannelService
from src.integrations.app.env_service import EnvService
from src.integrations.app.link_service import LinkService
from src.integrations.app.mcp_service import McpService
from src.integrations.app.template_service import TemplateService


class IntegrationsApp:
    def __init__(
        self,
        envs: EnvService,
        channels: ChannelService,
        mcp: McpService,
        templates: TemplateService,
        links: LinkService,
    ) -> None:
        self._envs = envs
        self._channels = channels
        self._mcp = mcp
        self._templates = templates
        self._links = links

    # --- Env ---

    async def create_env(self, workspace_id: UUID, name: str, values: dict, category: str | None = None) -> asyncpg.Record:
        return await self._envs.create(workspace_id, name, values, category)

    async def find_env(self, env_id: UUID) -> asyncpg.Record | None:
        return await self._envs.find(env_id)

    async def list_envs(self, workspace_id: UUID) -> list[asyncpg.Record]:
        return await self._envs.list(workspace_id)

    async def get_decrypted_env(self, env_id: UUID) -> dict:
        return await self._envs.get_decrypted(env_id)

    async def update_env(
        self, env_id: UUID, name: str | None = None, values: dict | None = None, category: str | None = None
    ) -> asyncpg.Record | None:
        return await self._envs.update(env_id, name=name, values=values, category=category)

    async def delete_env(self, env_id: UUID) -> None:
        await self._envs.delete(env_id)

    async def find_llm_provider(self, workspace_id: UUID) -> asyncpg.Record | None:
        return await self._envs.find_llm_provider(workspace_id)

    # --- Channel ---

    async def create_channel(self, workspace_id: UUID, name: str, type_: str, config: dict) -> asyncpg.Record:
        return await self._channels.create(workspace_id, name, type_, config)

    async def find_channel(self, channel_id: UUID) -> asyncpg.Record | None:
        return await self._channels.find(channel_id)

    async def list_channels(self, workspace_id: UUID) -> list[asyncpg.Record]:
        return await self._channels.list(workspace_id)

    async def get_decrypted_channel(self, channel_id: UUID) -> dict:
        return await self._channels.get_decrypted(channel_id)

    async def update_channel(
        self, channel_id: UUID, name: str | None = None, config: dict | None = None
    ) -> asyncpg.Record | None:
        return await self._channels.update(channel_id, name=name, config=config)

    async def delete_channel(self, channel_id: UUID) -> None:
        await self._channels.delete(channel_id)

    # --- MCP ---

    async def create_mcp(self, workspace_id: UUID, name: str, type_: str, config: dict) -> asyncpg.Record:
        return await self._mcp.create(workspace_id, name, type_, config)

    async def find_mcp(self, mcp_id: UUID) -> asyncpg.Record | None:
        return await self._mcp.find(mcp_id)

    async def list_mcps(self, workspace_id: UUID) -> list[asyncpg.Record]:
        return await self._mcp.list(workspace_id)

    async def get_decrypted_mcp(self, mcp_id: UUID) -> dict:
        return await self._mcp.get_decrypted(mcp_id)

    async def update_mcp(
        self, mcp_id: UUID, name: str | None = None, config: dict | None = None
    ) -> asyncpg.Record | None:
        return await self._mcp.update(mcp_id, name=name, config=config)

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
        self, workspace_id: UUID, name: str, template_type: str, content: str
    ) -> asyncpg.Record:
        return await self._templates.create(workspace_id, name, template_type, content)

    async def find_template(self, template_id: UUID) -> asyncpg.Record | None:
        return await self._templates.find(template_id)

    async def list_templates(self, workspace_id: UUID) -> list[asyncpg.Record]:
        return await self._templates.list(workspace_id)

    async def update_template(
        self, template_id: UUID, name: str | None = None, content: str | None = None
    ) -> asyncpg.Record | None:
        return await self._templates.update(template_id, name=name, content=content)

    async def delete_template(self, template_id: UUID) -> None:
        await self._templates.delete(template_id)

    # --- Links: templates ---

    async def attach_template(self, agent_id: UUID, template_id: UUID, template_type: str) -> None:
        await self._links.attach_template(agent_id, template_id, template_type)

    async def detach_template(self, agent_id: UUID, template_id: UUID) -> None:
        await self._links.detach_template(agent_id, template_id)

    async def list_agent_templates(self, agent_id: UUID) -> list[asyncpg.Record]:
        return await self._links.list_templates(agent_id)
