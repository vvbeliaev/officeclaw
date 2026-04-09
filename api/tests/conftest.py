# api/tests/conftest.py
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import UUID

import asyncpg
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.shared.db.pool import get_pool
from src.ports.rest.main import create_app

TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5434/officeclaw_test",
)

MIGRATIONS_DIR = Path(__file__).parent.parent / "migrations" / "versions"


@pytest.fixture(scope="session")
async def raw_pool():
    pool = await asyncpg.create_pool(TEST_DB_URL)
    yield pool
    await pool.close()


@pytest.fixture(scope="session", autouse=True)
async def run_migrations(raw_pool: asyncpg.Pool) -> AsyncGenerator[None, None]:
    for sql_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
        sql = sql_file.read_text()
        async with raw_pool.acquire() as conn:
            await conn.execute(sql)
    yield
    async with raw_pool.acquire() as conn:
        await conn.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")


@pytest.fixture()
async def conn(raw_pool: asyncpg.Pool) -> AsyncGenerator[asyncpg.Connection, None]:
    connection = await raw_pool.acquire()
    tr = connection.transaction()
    await tr.start()
    try:
        yield connection
    finally:
        await tr.rollback()
        await raw_pool.release(connection)


@pytest.fixture()
async def client(conn: asyncpg.Connection) -> AsyncGenerator[AsyncClient, None]:
    app = create_app()

    @asynccontextmanager
    async def noop_lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        yield

    app.router.lifespan_context = noop_lifespan
    app.dependency_overrides[get_pool] = lambda: conn

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
async def mcp_user(client):
    """Create a user and return (user_id, token)."""
    resp = await client.post("/users", json={"email": "mcp-user@example.com"})
    body = resp.json()
    return body["id"], body["officeclaw_token"]


@pytest.fixture
async def mcp_conn_user(conn, mcp_user):
    """Return (conn, user_id) — conn is the test transaction connection."""
    user_id, _ = mcp_user
    return conn, UUID(user_id)
