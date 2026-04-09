import asyncpg
from fastapi import FastAPI, Request


async def create_pool(app: FastAPI) -> None:
    from src.config import get_settings
    app.state.pool = await asyncpg.create_pool(get_settings().database_url)


async def close_pool(app: FastAPI) -> None:
    await app.state.pool.close()


def get_pool(request: Request) -> asyncpg.Pool:
    return request.app.state.pool
