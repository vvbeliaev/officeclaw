import asyncpg

from src.integrations.adapters.out.repository import (
    AgentMcpRepo,
    ChannelRepo,
    EnvRepo,
    LinkRepo,
)
from src.integrations.app import IntegrationsApp


def build(pool: asyncpg.Pool) -> IntegrationsApp:
    return IntegrationsApp(
        env_repo=EnvRepo(pool),
        channel_repo=ChannelRepo(pool),
        link_repo=LinkRepo(pool),
        mcp_repo=AgentMcpRepo(pool),
    )
