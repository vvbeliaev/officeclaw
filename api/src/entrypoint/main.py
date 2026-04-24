from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI

from src.shared.config import get_settings
from src.shared.storage import S3Storage
import src.fleet.di as fleet_di
import src.identity.di as identity_di
import src.library.di as library_di
import src.integrations.di as integrations_di
import src.knowledge.di as knowledge_di
import src.workspace.di as workspace_di
from src.fleet.adapters._in.router import router as agents_router
from src.identity.adapters._in.router import router as users_router
from src.integrations.adapters._in.router import (
    envs_router,
    channels_router,
    mcp_router,
    templates_router,
    links_router,
)
from src.library.adapters._in.router import router as skills_router
from src.knowledge.adapters._in.router import router as knowledge_router
from src.workspace.adapters._in.router import router as workspaces_router

from .mcp import admin_mcp, knowledge_mcp, setup as mcp_setup

_admin_mcp_asgi = admin_mcp.http_app(path="/")
_knowledge_mcp_asgi = knowledge_mcp.http_app(path="/")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    pool = await asyncpg.create_pool(settings.database_url)

    storage = S3Storage(
        endpoint=settings.storage_endpoint,
        access_key=settings.storage_access_key,
        secret_key=settings.storage_secret_key,
        bucket=settings.storage_bucket,
        public_base_url=settings.storage_public_base_url,
    )

    integrations = integrations_di.build(pool)
    library = library_di.build(pool)
    fleet, sandbox, watcher = fleet_di.build(pool, integrations, library)
    workspace = workspace_di.build(pool, fleet, integrations)
    fleet_di.bind_workspace(sandbox, workspace)
    identity = identity_di.build(pool, workspace)
    knowledge = knowledge_di.build(settings)

    app.state.pool = pool
    app.state.fleet = fleet
    app.state.identity = identity
    app.state.library = library
    app.state.integrations = integrations
    app.state.workspace = workspace
    app.state.knowledge = knowledge
    app.state.storage = storage

    mcp_setup(
        pool=pool,
        fleet=fleet,
        workspace=workspace,
        library=library,
        integrations=integrations,
        knowledge=knowledge,
    )

    watcher.start()

    async with _admin_mcp_asgi.lifespan(_admin_mcp_asgi):
        async with _knowledge_mcp_asgi.lifespan(_knowledge_mcp_asgi):
            yield

    await watcher.stop()
    await pool.close()


def create_app() -> FastAPI:
    app = FastAPI(title="OfficeClaw API", lifespan=lifespan)
    app.include_router(users_router, prefix="/users", tags=["users"])
    app.include_router(workspaces_router, prefix="/workspaces", tags=["workspaces"])
    app.include_router(agents_router, prefix="/agents", tags=["agents"])
    app.include_router(skills_router, prefix="/skills", tags=["skills"])
    app.include_router(envs_router, prefix="/envs", tags=["envs"])
    app.include_router(channels_router, prefix="/channels", tags=["channels"])
    app.include_router(mcp_router, prefix="/user-mcp", tags=["mcp"])
    app.include_router(templates_router, prefix="/templates", tags=["templates"])
    app.include_router(links_router, tags=["links"])
    app.include_router(knowledge_router, prefix="/knowledge", tags=["knowledge"])

    app.mount("/mcp/admin", _admin_mcp_asgi)
    app.mount("/mcp/knowledge", _knowledge_mcp_asgi)

    return app


app = create_app()
