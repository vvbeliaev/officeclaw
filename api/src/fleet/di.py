import asyncpg

from src.fleet.adapters.out.repository import AgentFileRepo, AgentRepo
from src.fleet.app import FleetApp
from src.fleet.app.agents import AgentService
from src.fleet.app.sandbox import SandboxService
from src.integrations.app import IntegrationsApp
from src.library.app import LibraryApp


def build(
    pool: asyncpg.Pool,
    integrations: IntegrationsApp,
    library: LibraryApp,
) -> FleetApp:
    agents = AgentService(AgentRepo(pool), AgentFileRepo(pool))
    sandbox = SandboxService(agents, integrations, library)
    return FleetApp(agents, sandbox)
