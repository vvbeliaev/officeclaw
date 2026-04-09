import asyncio
import os
import pytest
import asyncpg
from httpx import AsyncClient, ASGITransport
from src.main import create_app

TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql://officeclaw:officeclaw@localhost:5432/officeclaw_test"
)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def raw_pool():
    pool = await asyncpg.create_pool(TEST_DB_URL)
    yield pool
    await pool.close()


@pytest.fixture(scope="session", autouse=True)
async def run_migrations(raw_pool):
    """Run all migrations against test DB before session."""
    async with raw_pool.acquire() as conn:
        with open("migrations/versions/001_initial_schema.sql") as f:
            await conn.execute(f.read())
    yield
    async with raw_pool.acquire() as conn:
        await conn.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")


@pytest.fixture()
async def conn(raw_pool):
    async with raw_pool.acquire() as connection:
        tr = connection.transaction()
        await tr.start()
        yield connection
        await tr.rollback()


@pytest.fixture()
async def client(conn):
    app = create_app()
    # Override pool to use test connection
    app.state.pool = conn
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
