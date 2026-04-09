import asyncpg

from src.fleet.app import FleetApp
from src.identity.adapters.out.repository import UserRepo
from src.identity.app import IdentityApp
from src.integrations.app import IntegrationsApp


def build(
    pool: asyncpg.Pool,
    fleet: FleetApp,
    integrations: IntegrationsApp,
) -> IdentityApp:
    return IdentityApp(UserRepo(pool), fleet, integrations)
