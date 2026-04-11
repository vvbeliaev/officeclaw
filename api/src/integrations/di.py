import asyncpg

from src.integrations.adapters.out.repository import (
    ChannelRepo,
    EnvRepo,
    LinkRepo,
    UserMcpRepo,
    UserTemplateRepo,
)
from src.integrations.app import IntegrationsApp


def build(pool: asyncpg.Pool) -> IntegrationsApp:
    return IntegrationsApp(
        env_repo=EnvRepo(pool),
        channel_repo=ChannelRepo(pool),
        link_repo=LinkRepo(pool),
        mcp_repo=UserMcpRepo(pool),
        template_repo=UserTemplateRepo(pool),
    )
