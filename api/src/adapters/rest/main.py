# api/src/ports/rest/main.py
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.shared.db.pool import create_pool, close_pool
from src.adapters.mcp.server import mcp, set_pool
from src.identity.adapters.router import router as users_router
from src.library.adapters.router import router as skills_router
from src.fleet.adapters.router import router as agents_router
from src.integrations.adapters.router import envs_router, channels_router, links_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await create_pool(app)
    set_pool(app.state.pool)

    yield

    await close_pool(app)


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
