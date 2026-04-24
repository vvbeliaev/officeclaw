import asyncpg

from src.integrations.adapters.out.channel_repo import ChannelRepo
from src.integrations.adapters.out.cron_repo import WorkspaceCronRepo
from src.integrations.adapters.out.env_repo import EnvRepo
from src.integrations.adapters.out.links.channel_link_repo import ChannelLinkRepo
from src.integrations.adapters.out.links.cron_link_repo import CronLinkRepo
from src.integrations.adapters.out.links.env_link_repo import EnvLinkRepo
from src.integrations.adapters.out.links.mcp_link_repo import McpLinkRepo
from src.integrations.adapters.out.links.skill_link_repo import SkillLinkRepo
from src.integrations.adapters.out.links.template_link_repo import TemplateLinkRepo
from src.integrations.adapters.out.mcp_repo import UserMcpRepo
from src.integrations.adapters.out.template_repo import UserTemplateRepo
from src.integrations.app import IntegrationsApp
from src.integrations.app.channel_service import ChannelService
from src.integrations.app.cron_service import CronService
from src.integrations.app.env_service import EnvService
from src.integrations.app.link_service import LinkService
from src.integrations.app.mcp_service import McpService
from src.integrations.app.template_service import TemplateService


def build(pool: asyncpg.Pool) -> IntegrationsApp:
    return IntegrationsApp(
        envs=EnvService(EnvRepo(pool)),
        channels=ChannelService(ChannelRepo(pool)),
        mcp=McpService(UserMcpRepo(pool)),
        templates=TemplateService(UserTemplateRepo(pool)),
        crons=CronService(WorkspaceCronRepo(pool)),
        links=LinkService(
            skills=SkillLinkRepo(pool),
            envs=EnvLinkRepo(pool),
            channels=ChannelLinkRepo(pool),
            mcps=McpLinkRepo(pool),
            templates=TemplateLinkRepo(pool),
            crons=CronLinkRepo(pool),
        ),
    )
