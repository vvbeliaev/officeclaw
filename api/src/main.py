# api/src/main.py
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.db.pool import create_pool, close_pool
from src.mcp_server import mcp, set_pool
from src.routers import users, agents, skills, envs, channels, links


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await create_pool(app)
    set_pool(app.state.pool)
    yield
    await close_pool(app)


def create_app() -> FastAPI:
    app = FastAPI(title="OfficeClaw API", lifespan=lifespan)
    app.include_router(users.router, prefix="/users", tags=["users"])
    app.include_router(agents.router, prefix="/agents", tags=["agents"])
    app.include_router(skills.router, prefix="/skills", tags=["skills"])
    app.include_router(envs.router, prefix="/envs", tags=["envs"])
    app.include_router(channels.router, prefix="/channels", tags=["channels"])
    app.include_router(links.router, tags=["links"])
    app.mount("/mcp", mcp.http_app())
    return app


app = create_app()
