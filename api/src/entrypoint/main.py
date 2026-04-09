from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI

from src.shared.config import get_settings
import src.fleet.di as fleet_di
import src.identity.di as identity_di
import src.library.di as library_di
import src.integrations.di as integrations_di
from src.fleet.adapters._in.router import router as agents_router
from src.identity.adapters._in.router import router as users_router
from src.integrations.adapters._in.router import (
    envs_router,
    channels_router,
    links_router,
)
from src.library.adapters._in.router import router as skills_router

from .mcp import mcp, setup as mcp_setup


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    pool = await asyncpg.create_pool(settings.database_url)

    integrations = integrations_di.build(pool)
    library = library_di.build(pool)
    fleet = fleet_di.build(pool, integrations, library)
    identity = identity_di.build(pool, fleet, integrations)

    app.state.pool = pool
    app.state.fleet = fleet
    app.state.identity = identity
    app.state.library = library
    app.state.integrations = integrations

    mcp_setup(
        pool=pool,
        fleet=fleet,
        identity=identity,
        library=library,
        integrations=integrations,
    )

    yield

    await pool.close()


def create_app() -> FastAPI:
    app = FastAPI(title="OfficeClaw API", lifespan=lifespan)
    app.include_router(users_router, prefix="/users", tags=["users"])
    app.include_router(agents_router, prefix="/agents", tags=["agents"])
    app.include_router(skills_router, prefix="/skills", tags=["skills"])
    app.include_router(envs_router, prefix="/envs", tags=["envs"])
    app.include_router(channels_router, prefix="/channels", tags=["channels"])
    app.include_router(links_router, tags=["links"])

    app.mount("/mcp", mcp.http_app())

    return app


app = create_app()
