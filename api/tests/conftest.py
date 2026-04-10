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

from src.entrypoint.main import create_app
from src.shared.config import get_settings
import src.fleet.di as fleet_di
import src.identity.di as identity_di
import src.library.di as library_di
import src.integrations.di as integrations_di
from src.entrypoint.mcp import setup as mcp_setup

# Prime the cached Settings instance at import time. Some tests patch
# `builtins.open` (e.g. tests/test_sandbox.py), which breaks
# pydantic-settings if it tries to read .env for the first time inside
# the patched scope. Loading settings here guarantees the LRU cache
# already holds a valid instance.
get_settings()

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
        async with raw_pool.acquire() as c:
            await c.execute(sql)
    yield
    async with raw_pool.acquire() as c:
        await c.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")


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

    # Wire domain containers from the transactional test connection so every
    # request shares the same rolled-back transaction.
    pool = conn  # type: ignore[assignment]
    integrations = integrations_di.build(pool)  # type: ignore[arg-type]
    library = library_di.build(pool)  # type: ignore[arg-type]
    fleet = fleet_di.build(pool, integrations, library)  # type: ignore[arg-type]
    identity = identity_di.build(pool, fleet, integrations)  # type: ignore[arg-type]

    app.state.pool = pool
    app.state.fleet = fleet
    app.state.identity = identity
    app.state.library = library
    app.state.integrations = integrations
    mcp_setup(
        pool=pool,  # type: ignore[arg-type]
        fleet=fleet,
        identity=identity,
        library=library,
        integrations=integrations,
    )

    @asynccontextmanager
    async def noop_lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        yield

    app.router.lifespan_context = noop_lifespan

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


@pytest.fixture
def integrations_deps(conn):
    return integrations_di.build(conn)  # type: ignore[arg-type]


@pytest.fixture
def library_deps(conn):
    return library_di.build(conn)  # type: ignore[arg-type]


@pytest.fixture
def fleet_deps(conn, integrations_deps, library_deps):
    return fleet_di.build(conn, integrations_deps, library_deps)  # type: ignore[arg-type]
