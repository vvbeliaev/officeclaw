from uuid import UUID

import asyncpg

from src.integrations.adapters.out.links.channel_link_repo import ChannelLinkRepo
from src.integrations.adapters.out.links.cron_link_repo import CronLinkRepo
from src.integrations.adapters.out.links.env_link_repo import EnvLinkRepo
from src.integrations.adapters.out.links.mcp_link_repo import McpLinkRepo
from src.integrations.adapters.out.links.skill_link_repo import SkillLinkRepo
from src.integrations.adapters.out.links.template_link_repo import TemplateLinkRepo


class LinkService:
    def __init__(
        self,
        skills: SkillLinkRepo,
        envs: EnvLinkRepo,
        channels: ChannelLinkRepo,
        mcps: McpLinkRepo,
        templates: TemplateLinkRepo,
        crons: CronLinkRepo,
    ) -> None:
        self._skills = skills
        self._envs = envs
        self._channels = channels
        self._mcps = mcps
        self._templates = templates
        self._crons = crons

    # --- Skills ---

    async def attach_skill(self, agent_id: UUID, skill_id: UUID) -> None:
        await self._skills.attach(agent_id, skill_id)

    async def detach_skill(self, agent_id: UUID, skill_id: UUID) -> None:
        await self._skills.detach(agent_id, skill_id)

    async def list_skills(self, agent_id: UUID) -> list[asyncpg.Record]:
        return await self._skills.list_by_agent(agent_id)

    # --- Envs ---

    async def attach_env(self, agent_id: UUID, env_id: UUID) -> None:
        await self._envs.attach(agent_id, env_id)

    async def detach_env(self, agent_id: UUID, env_id: UUID) -> None:
        await self._envs.detach(agent_id, env_id)

    async def list_envs(self, agent_id: UUID) -> list[asyncpg.Record]:
        return await self._envs.list_by_agent(agent_id)

    # --- Channels ---

    async def attach_channel(self, agent_id: UUID, channel_id: UUID) -> None:
        await self._channels.attach(agent_id, channel_id)

    async def detach_channel(self, agent_id: UUID, channel_id: UUID) -> None:
        await self._channels.detach(agent_id, channel_id)

    async def list_channels(self, agent_id: UUID) -> list[asyncpg.Record]:
        return await self._channels.list_by_agent(agent_id)

    # --- MCPs ---

    async def attach_mcp(self, agent_id: UUID, mcp_id: UUID) -> None:
        await self._mcps.attach(agent_id, mcp_id)

    async def detach_mcp(self, agent_id: UUID, mcp_id: UUID) -> None:
        await self._mcps.detach(agent_id, mcp_id)

    async def list_mcps(self, agent_id: UUID) -> list[asyncpg.Record]:
        return await self._mcps.list_by_agent(agent_id)

    async def list_mcps_decrypted(self, agent_id: UUID) -> list[dict]:
        return await self._mcps.list_decrypted(agent_id)

    # --- Templates ---

    async def attach_template(self, agent_id: UUID, template_id: UUID, template_type: str) -> None:
        await self._templates.attach(agent_id, template_id, template_type)

    async def detach_template(self, agent_id: UUID, template_id: UUID) -> None:
        await self._templates.detach(agent_id, template_id)

    async def list_templates(self, agent_id: UUID) -> list[asyncpg.Record]:
        return await self._templates.list_by_agent(agent_id)

    # --- Crons ---

    async def attach_cron(self, agent_id: UUID, cron_id: UUID, enabled: bool = True) -> None:
        await self._crons.attach(agent_id, cron_id, enabled)

    async def detach_cron(self, agent_id: UUID, cron_id: UUID) -> None:
        await self._crons.detach(agent_id, cron_id)

    async def set_cron_enabled(self, agent_id: UUID, cron_id: UUID, enabled: bool) -> asyncpg.Record | None:
        return await self._crons.set_enabled(agent_id, cron_id, enabled)

    async def list_crons(self, agent_id: UUID) -> list[dict]:
        return await self._crons.list_by_agent(agent_id)
