# API Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Python FastAPI backend with full DB schema, repositories, and REST endpoints for users, agents, agent_files, skills, user_envs, user_channels, agent_mcp, and M:M link tables.

**Architecture:** FastAPI app with asyncpg (raw SQL, no ORM). Pydantic v2 for request/response models. Alembic for migrations. Secrets encrypted with Fernet (AES-128) at the application layer before storage.

**Tech Stack:** Python 3.13, FastAPI, asyncpg, Alembic, Pydantic v2, cryptography (Fernet), pytest, pytest-asyncio, httpx

---

## File Map

```
api/
  src/
    main.py                    # FastAPI app factory + lifespan
    config.py                  # Settings from env vars (pydantic-settings)
    crypto.py                  # Fernet encrypt/decrypt helpers
    db/
      pool.py                  # asyncpg pool creation + app state
    repositories/
      users.py                 # UserRepo: find_by_id, find_by_email, create
      agents.py                # AgentRepo: CRUD + status update
      agent_files.py           # AgentFileRepo: upsert, list, bulk_upsert
      skills.py                # SkillRepo + SkillFileRepo
      envs.py                  # EnvRepo: CRUD with encrypt/decrypt
      channels.py              # ChannelRepo: CRUD with encrypt/decrypt
      mcp.py                   # AgentMcpRepo: CRUD with encrypt/decrypt
      links.py                 # M:M: agent_skills, agent_envs, agent_channels
    models/
      user.py                  # UserCreate, UserOut
      agent.py                 # AgentCreate, AgentOut, AgentUpdate
      agent_file.py            # AgentFileIn, AgentFileOut
      skill.py                 # SkillCreate, SkillOut, SkillFileIn
      env.py                   # EnvCreate, EnvOut (values never returned)
      channel.py               # ChannelCreate, ChannelOut (config never returned)
      mcp.py                   # McpCreate, McpOut
    routers/
      users.py                 # POST /users, GET /users/{id}
      agents.py                # CRUD /agents, /agents/{id}/files
      skills.py                # CRUD /skills, /skills/{id}/files
      envs.py                  # CRUD /envs
      channels.py              # CRUD /channels
      links.py                 # POST/DELETE /agents/{id}/skills|envs|channels|mcp
    vm_payload.py              # Assembles sandbox-manager start payload from DB
  migrations/
    alembic.ini
    env.py
    versions/
      001_initial_schema.py
  tests/
    conftest.py                # DB pool fixture, app test client, factories
    test_users.py
    test_agents.py
    test_agent_files.py
    test_skills.py
    test_envs.py
    test_channels.py
    test_links.py
    test_vm_payload.py
  pyproject.toml
  .env.example
```

---

## Task 1: Project Setup

**Files:**
- Create: `api/pyproject.toml`
- Create: `api/src/main.py`
- Create: `api/src/config.py`
- Create: `api/.env.example`

- [ ] **Step 1.1: Replace pyproject.toml with dependencies**

```toml
# api/pyproject.toml
[project]
name = "api"
version = "0.1.0"
description = "OfficeClaw control plane API"
readme = "README.md"
requires-python = ">=3.13"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.32",
    "asyncpg>=0.30",
    "pydantic>=2.9",
    "pydantic-settings>=2.6",
    "alembic>=1.14",
    "cryptography>=43",
    "python-dotenv>=1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8",
    "pytest-asyncio>=0.24",
    "httpx>=0.27",
    "pytest-cov>=6",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 1.2: Create config.py**

```python
# api/src/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    encryption_key: str  # base64-encoded 32-byte Fernet key
    debug: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
```

- [ ] **Step 1.3: Create .env.example**

```bash
# api/.env.example
DATABASE_URL=postgresql://officeclaw:officeclaw@localhost:5432/officeclaw
# Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ENCRYPTION_KEY=your-fernet-key-here
DEBUG=false
```

- [ ] **Step 1.4: Create main.py**

```python
# api/src/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from src.db.pool import create_pool, close_pool
from src.routers import users, agents, skills, envs, channels, links


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_pool(app)
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
    return app


app = create_app()
```

- [ ] **Step 1.5: Verify the app imports without error**

```bash
cd api && pip install -e ".[dev]" && python -c "from src.main import app; print('ok')"
```

Expected: `ok`

- [ ] **Step 1.6: Commit**

```bash
git add api/pyproject.toml api/src/main.py api/src/config.py api/.env.example
git commit -m "feat(api): project scaffold — FastAPI app + config"
```

---

## Task 2: DB Connection Pool

**Files:**
- Create: `api/src/db/pool.py`
- Create: `api/tests/conftest.py`

- [ ] **Step 2.1: Write the failing test**

```python
# api/tests/conftest.py
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
```

- [ ] **Step 2.2: Create pool.py**

```python
# api/src/db/pool.py
import asyncpg
from fastapi import FastAPI, Request


async def create_pool(app: FastAPI) -> None:
    from src.config import settings
    app.state.pool = await asyncpg.create_pool(settings.database_url)


async def close_pool(app: FastAPI) -> None:
    await app.state.pool.close()


def get_pool(request: Request) -> asyncpg.Pool:
    return request.app.state.pool
```

- [ ] **Step 2.3: Run import check**

```bash
cd api && python -c "from src.db.pool import get_pool; print('ok')"
```

Expected: `ok`

- [ ] **Step 2.4: Commit**

```bash
git add api/src/db/pool.py api/tests/conftest.py
git commit -m "feat(api): asyncpg pool + test fixtures"
```

---

## Task 3: DB Migrations — Initial Schema

**Files:**
- Create: `api/migrations/alembic.ini`
- Create: `api/migrations/env.py`
- Create: `api/migrations/versions/001_initial_schema.sql`

- [ ] **Step 3.1: Create alembic.ini**

```ini
# api/migrations/alembic.ini
[alembic]
script_location = migrations
sqlalchemy.url = %(DATABASE_URL)s
```

- [ ] **Step 3.2: Create the SQL migration file**

```sql
-- api/migrations/versions/001_initial_schema.sql
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TYPE agent_status AS ENUM ('idle', 'running', 'error');

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    status agent_status NOT NULL DEFAULT 'idle',
    sandbox_id TEXT,
    image TEXT NOT NULL DEFAULT 'ghcr.io/hkuds/nanobot:latest',
    is_admin BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE agent_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    path TEXT NOT NULL,
    content TEXT NOT NULL DEFAULT '',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(agent_id, path)
);

CREATE TABLE skills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE skill_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    path TEXT NOT NULL,
    content TEXT NOT NULL DEFAULT '',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(skill_id, path)
);

CREATE TABLE user_envs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    values_encrypted BYTEA NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, name)
);

CREATE TABLE user_channels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    config_encrypted BYTEA NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE agent_mcp (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    config_encrypted BYTEA NOT NULL,
    UNIQUE(agent_id, name)
);

CREATE TABLE agent_skills (
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    PRIMARY KEY (agent_id, skill_id)
);

CREATE TABLE agent_envs (
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    env_id UUID NOT NULL REFERENCES user_envs(id) ON DELETE CASCADE,
    PRIMARY KEY (agent_id, env_id)
);

CREATE TABLE agent_channels (
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    channel_id UUID NOT NULL REFERENCES user_channels(id) ON DELETE CASCADE,
    PRIMARY KEY (agent_id, channel_id)
);
```

- [ ] **Step 3.3: Apply migration to dev DB**

```bash
cd api && psql $DATABASE_URL -f migrations/versions/001_initial_schema.sql
```

Expected: series of `CREATE TABLE` messages, no errors.

- [ ] **Step 3.4: Commit**

```bash
git add api/migrations/
git commit -m "feat(api): initial DB schema — all tables"
```

---

## Task 4: Crypto Utility

**Files:**
- Create: `api/src/crypto.py`
- Create: `api/tests/test_crypto.py`

- [ ] **Step 4.1: Write the failing test**

```python
# api/tests/test_crypto.py
import pytest
from src.crypto import encrypt_json, decrypt_json


def test_encrypt_decrypt_roundtrip():
    data = {"ANTHROPIC_API_KEY": "sk-ant-123", "TELEGRAM_TOKEN": "bot:456"}
    encrypted = encrypt_json(data)
    assert isinstance(encrypted, bytes)
    assert encrypted != str(data).encode()
    result = decrypt_json(encrypted)
    assert result == data


def test_encrypt_produces_different_ciphertext_each_time():
    data = {"key": "value"}
    enc1 = encrypt_json(data)
    enc2 = encrypt_json(data)
    assert enc1 != enc2  # Fernet uses random IV
```

- [ ] **Step 4.2: Run to verify it fails**

```bash
cd api && pytest tests/test_crypto.py -v
```

Expected: `ImportError` or `ModuleNotFoundError`

- [ ] **Step 4.3: Implement crypto.py**

```python
# api/src/crypto.py
import json
from cryptography.fernet import Fernet
from src.config import settings

_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = Fernet(settings.encryption_key.encode())
    return _fernet


def encrypt_json(data: dict) -> bytes:
    return _get_fernet().encrypt(json.dumps(data).encode())


def decrypt_json(ciphertext: bytes) -> dict:
    return json.loads(_get_fernet().decrypt(ciphertext))
```

- [ ] **Step 4.4: Run tests**

```bash
cd api && pytest tests/test_crypto.py -v
```

Expected: `2 passed`

- [ ] **Step 4.5: Commit**

```bash
git add api/src/crypto.py api/tests/test_crypto.py
git commit -m "feat(api): Fernet encrypt/decrypt for secrets"
```

---

## Task 5: Users

**Files:**
- Create: `api/src/models/user.py`
- Create: `api/src/repositories/users.py`
- Create: `api/src/routers/users.py`
- Create: `api/tests/test_users.py`

- [ ] **Step 5.1: Write the failing tests**

```python
# api/tests/test_users.py
import pytest


async def test_create_user(client):
    resp = await client.post("/users", json={"email": "alice@example.com"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "alice@example.com"
    assert "id" in body
    assert "created_at" in body


async def test_create_user_duplicate_email(client):
    await client.post("/users", json={"email": "bob@example.com"})
    resp = await client.post("/users", json={"email": "bob@example.com"})
    assert resp.status_code == 409


async def test_get_user(client):
    create = await client.post("/users", json={"email": "carol@example.com"})
    user_id = create.json()["id"]
    resp = await client.get(f"/users/{user_id}")
    assert resp.status_code == 200
    assert resp.json()["email"] == "carol@example.com"


async def test_get_user_not_found(client):
    resp = await client.get("/users/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404
```

- [ ] **Step 5.2: Run to verify they fail**

```bash
cd api && pytest tests/test_users.py -v
```

Expected: 4 errors (router/model not defined)

- [ ] **Step 5.3: Create models/user.py**

```python
# api/src/models/user.py
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr


class UserOut(BaseModel):
    id: UUID
    email: str
    created_at: datetime
```

- [ ] **Step 5.4: Create repositories/users.py**

```python
# api/src/repositories/users.py
from uuid import UUID
import asyncpg


class UserRepo:
    def __init__(self, conn: asyncpg.Connection):
        self._conn = conn

    async def create(self, email: str) -> asyncpg.Record:
        return await self._conn.fetchrow(
            "INSERT INTO users (email) VALUES ($1) RETURNING *", email
        )

    async def find_by_id(self, user_id: UUID) -> asyncpg.Record | None:
        return await self._conn.fetchrow(
            "SELECT * FROM users WHERE id = $1", user_id
        )

    async def find_by_email(self, email: str) -> asyncpg.Record | None:
        return await self._conn.fetchrow(
            "SELECT * FROM users WHERE email = $1", email
        )
```

- [ ] **Step 5.5: Create routers/users.py**

```python
# api/src/routers/users.py
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
import asyncpg
from src.db.pool import get_pool
from src.models.user import UserCreate, UserOut
from src.repositories.users import UserRepo

router = APIRouter()


def get_repo(pool: asyncpg.Pool = Depends(get_pool)) -> UserRepo:
    # Note: in tests, pool is a connection; in prod, pool is a Pool.
    # Routers acquire connection per-request.
    return UserRepo(pool)


@router.post("", response_model=UserOut, status_code=201)
async def create_user(body: UserCreate, repo: UserRepo = Depends(get_repo)):
    try:
        record = await repo.create(body.email)
    except asyncpg.UniqueViolationError:
        raise HTTPException(409, "Email already registered")
    return dict(record)


@router.get("/{user_id}", response_model=UserOut)
async def get_user(user_id: UUID, repo: UserRepo = Depends(get_repo)):
    record = await repo.find_by_id(user_id)
    if not record:
        raise HTTPException(404, "User not found")
    return dict(record)
```

- [ ] **Step 5.6: Run tests**

```bash
cd api && pytest tests/test_users.py -v
```

Expected: `4 passed`

- [ ] **Step 5.7: Commit**

```bash
git add api/src/models/user.py api/src/repositories/users.py api/src/routers/users.py api/tests/test_users.py
git commit -m "feat(api): users — model, repo, router, tests"
```

---

## Task 6: Agents

**Files:**
- Create: `api/src/models/agent.py`
- Create: `api/src/repositories/agents.py`
- Create: `api/src/routers/agents.py`
- Create: `api/tests/test_agents.py`

- [ ] **Step 6.1: Write the failing tests**

```python
# api/tests/test_agents.py
import pytest


@pytest.fixture
async def user_id(client):
    resp = await client.post("/users", json={"email": "agent-owner@example.com"})
    return resp.json()["id"]


async def test_create_agent(client, user_id):
    resp = await client.post("/agents", json={
        "user_id": user_id, "name": "My Agent"
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "My Agent"
    assert body["status"] == "idle"
    assert body["is_admin"] is False


async def test_list_agents_for_user(client, user_id):
    await client.post("/agents", json={"user_id": user_id, "name": "A1"})
    await client.post("/agents", json={"user_id": user_id, "name": "A2"})
    resp = await client.get(f"/agents?user_id={user_id}")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_update_agent_status(client, user_id):
    create = await client.post("/agents", json={"user_id": user_id, "name": "A"})
    agent_id = create.json()["id"]
    resp = await client.patch(f"/agents/{agent_id}", json={"status": "running", "sandbox_id": "sb-123"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "running"
    assert resp.json()["sandbox_id"] == "sb-123"


async def test_delete_agent(client, user_id):
    create = await client.post("/agents", json={"user_id": user_id, "name": "A"})
    agent_id = create.json()["id"]
    resp = await client.delete(f"/agents/{agent_id}")
    assert resp.status_code == 204
    resp2 = await client.get(f"/agents/{agent_id}")
    assert resp2.status_code == 404
```

- [ ] **Step 6.2: Run to verify they fail**

```bash
cd api && pytest tests/test_agents.py -v
```

Expected: 4 errors

- [ ] **Step 6.3: Create models/agent.py**

```python
# api/src/models/agent.py
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel
from typing import Literal


AgentStatus = Literal["idle", "running", "error"]


class AgentCreate(BaseModel):
    user_id: UUID
    name: str
    image: str = "ghcr.io/hkuds/nanobot:latest"
    is_admin: bool = False


class AgentUpdate(BaseModel):
    name: str | None = None
    status: AgentStatus | None = None
    sandbox_id: str | None = None


class AgentOut(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    status: str
    sandbox_id: str | None
    image: str
    is_admin: bool
    created_at: datetime
    updated_at: datetime
```

- [ ] **Step 6.4: Create repositories/agents.py**

```python
# api/src/repositories/agents.py
from uuid import UUID
import asyncpg


class AgentRepo:
    def __init__(self, conn: asyncpg.Connection):
        self._conn = conn

    async def create(self, user_id: UUID, name: str, image: str, is_admin: bool) -> asyncpg.Record:
        return await self._conn.fetchrow(
            """INSERT INTO agents (user_id, name, image, is_admin)
               VALUES ($1, $2, $3, $4) RETURNING *""",
            user_id, name, image, is_admin,
        )

    async def find_by_id(self, agent_id: UUID) -> asyncpg.Record | None:
        return await self._conn.fetchrow("SELECT * FROM agents WHERE id = $1", agent_id)

    async def list_by_user(self, user_id: UUID) -> list[asyncpg.Record]:
        return await self._conn.fetch("SELECT * FROM agents WHERE user_id = $1", user_id)

    async def update(self, agent_id: UUID, **fields) -> asyncpg.Record | None:
        set_clauses = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(fields))
        values = list(fields.values())
        return await self._conn.fetchrow(
            f"UPDATE agents SET {set_clauses}, updated_at = NOW() WHERE id = $1 RETURNING *",
            agent_id, *values,
        )

    async def delete(self, agent_id: UUID) -> None:
        await self._conn.execute("DELETE FROM agents WHERE id = $1", agent_id)
```

- [ ] **Step 6.5: Create routers/agents.py**

```python
# api/src/routers/agents.py
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
import asyncpg
from src.db.pool import get_pool
from src.models.agent import AgentCreate, AgentOut, AgentUpdate
from src.repositories.agents import AgentRepo

router = APIRouter()


def get_repo(pool=Depends(get_pool)) -> AgentRepo:
    return AgentRepo(pool)


@router.post("", response_model=AgentOut, status_code=201)
async def create_agent(body: AgentCreate, repo: AgentRepo = Depends(get_repo)):
    record = await repo.create(body.user_id, body.name, body.image, body.is_admin)
    return dict(record)


@router.get("", response_model=list[AgentOut])
async def list_agents(user_id: UUID, repo: AgentRepo = Depends(get_repo)):
    records = await repo.list_by_user(user_id)
    return [dict(r) for r in records]


@router.get("/{agent_id}", response_model=AgentOut)
async def get_agent(agent_id: UUID, repo: AgentRepo = Depends(get_repo)):
    record = await repo.find_by_id(agent_id)
    if not record:
        raise HTTPException(404, "Agent not found")
    return dict(record)


@router.patch("/{agent_id}", response_model=AgentOut)
async def update_agent(agent_id: UUID, body: AgentUpdate, repo: AgentRepo = Depends(get_repo)):
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(400, "No fields to update")
    record = await repo.update(agent_id, **updates)
    if not record:
        raise HTTPException(404, "Agent not found")
    return dict(record)


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(agent_id: UUID, repo: AgentRepo = Depends(get_repo)):
    record = await repo.find_by_id(agent_id)
    if not record:
        raise HTTPException(404, "Agent not found")
    await repo.delete(agent_id)
```

- [ ] **Step 6.6: Run tests**

```bash
cd api && pytest tests/test_agents.py -v
```

Expected: `4 passed`

- [ ] **Step 6.7: Commit**

```bash
git add api/src/models/agent.py api/src/repositories/agents.py api/src/routers/agents.py api/tests/test_agents.py
git commit -m "feat(api): agents — CRUD model, repo, router, tests"
```

---

## Task 7: Agent Files

**Files:**
- Create: `api/src/models/agent_file.py`
- Create: `api/src/repositories/agent_files.py`
- Modify: `api/src/routers/agents.py` (add file sub-routes)
- Create: `api/tests/test_agent_files.py`

- [ ] **Step 7.1: Write the failing tests**

```python
# api/tests/test_agent_files.py
import pytest


@pytest.fixture
async def agent_id(client):
    user = await client.post("/users", json={"email": "files-owner@example.com"})
    uid = user.json()["id"]
    agent = await client.post("/agents", json={"user_id": uid, "name": "Agent"})
    return agent.json()["id"]


async def test_upsert_and_get_file(client, agent_id):
    resp = await client.put(
        f"/agents/{agent_id}/files",
        json={"path": "SOUL.md", "content": "You are a helpful agent."}
    )
    assert resp.status_code == 200
    assert resp.json()["path"] == "SOUL.md"

    resp2 = await client.get(f"/agents/{agent_id}/files/SOUL.md")
    assert resp2.status_code == 200
    assert resp2.json()["content"] == "You are a helpful agent."


async def test_list_files(client, agent_id):
    await client.put(f"/agents/{agent_id}/files", json={"path": "SOUL.md", "content": "x"})
    await client.put(f"/agents/{agent_id}/files", json={"path": "AGENTS.md", "content": "y"})
    resp = await client.get(f"/agents/{agent_id}/files")
    assert resp.status_code == 200
    paths = [f["path"] for f in resp.json()]
    assert "SOUL.md" in paths
    assert "AGENTS.md" in paths


async def test_upsert_overwrites(client, agent_id):
    await client.put(f"/agents/{agent_id}/files", json={"path": "SOUL.md", "content": "v1"})
    await client.put(f"/agents/{agent_id}/files", json={"path": "SOUL.md", "content": "v2"})
    resp = await client.get(f"/agents/{agent_id}/files/SOUL.md")
    assert resp.json()["content"] == "v2"
```

- [ ] **Step 7.2: Run to verify they fail**

```bash
cd api && pytest tests/test_agent_files.py -v
```

Expected: 3 errors (routes not defined)

- [ ] **Step 7.3: Create models/agent_file.py**

```python
# api/src/models/agent_file.py
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class AgentFileIn(BaseModel):
    path: str
    content: str


class AgentFileOut(BaseModel):
    id: UUID
    agent_id: UUID
    path: str
    content: str
    updated_at: datetime
```

- [ ] **Step 7.4: Create repositories/agent_files.py**

```python
# api/src/repositories/agent_files.py
from uuid import UUID
import asyncpg


class AgentFileRepo:
    def __init__(self, conn: asyncpg.Connection):
        self._conn = conn

    async def upsert(self, agent_id: UUID, path: str, content: str) -> asyncpg.Record:
        return await self._conn.fetchrow(
            """INSERT INTO agent_files (agent_id, path, content)
               VALUES ($1, $2, $3)
               ON CONFLICT (agent_id, path)
               DO UPDATE SET content = EXCLUDED.content, updated_at = NOW()
               RETURNING *""",
            agent_id, path, content,
        )

    async def find(self, agent_id: UUID, path: str) -> asyncpg.Record | None:
        return await self._conn.fetchrow(
            "SELECT * FROM agent_files WHERE agent_id = $1 AND path = $2", agent_id, path
        )

    async def list_by_agent(self, agent_id: UUID) -> list[asyncpg.Record]:
        return await self._conn.fetch(
            "SELECT * FROM agent_files WHERE agent_id = $1 ORDER BY path", agent_id
        )

    async def bulk_upsert(self, agent_id: UUID, files: list[dict]) -> None:
        """Upsert multiple files — used during VM stop sync-back."""
        for f in files:
            await self.upsert(agent_id, f["path"], f["content"])
```

- [ ] **Step 7.5: Add file sub-routes to routers/agents.py**

Add these routes to the existing `api/src/routers/agents.py` (append after delete route):

```python
from src.models.agent_file import AgentFileIn, AgentFileOut
from src.repositories.agent_files import AgentFileRepo


def get_file_repo(pool=Depends(get_pool)) -> AgentFileRepo:
    return AgentFileRepo(pool)


@router.put("/{agent_id}/files", response_model=AgentFileOut)
async def upsert_file(
    agent_id: UUID,
    body: AgentFileIn,
    repo: AgentFileRepo = Depends(get_file_repo),
):
    record = await repo.upsert(agent_id, body.path, body.content)
    return dict(record)


@router.get("/{agent_id}/files", response_model=list[AgentFileOut])
async def list_files(agent_id: UUID, repo: AgentFileRepo = Depends(get_file_repo)):
    records = await repo.list_by_agent(agent_id)
    return [dict(r) for r in records]


@router.get("/{agent_id}/files/{path:path}", response_model=AgentFileOut)
async def get_file(agent_id: UUID, path: str, repo: AgentFileRepo = Depends(get_file_repo)):
    record = await repo.find(agent_id, path)
    if not record:
        raise HTTPException(404, "File not found")
    return dict(record)
```

- [ ] **Step 7.6: Run tests**

```bash
cd api && pytest tests/test_agent_files.py -v
```

Expected: `3 passed`

- [ ] **Step 7.7: Commit**

```bash
git add api/src/models/agent_file.py api/src/repositories/agent_files.py api/src/routers/agents.py api/tests/test_agent_files.py
git commit -m "feat(api): agent_files — upsert, list, get"
```

---

## Task 8: Skills

**Files:**
- Create: `api/src/models/skill.py`
- Create: `api/src/repositories/skills.py`
- Create: `api/src/routers/skills.py`
- Create: `api/tests/test_skills.py`

- [ ] **Step 8.1: Write the failing tests**

```python
# api/tests/test_skills.py
import pytest


@pytest.fixture
async def user_id(client):
    resp = await client.post("/users", json={"email": "skill-owner@example.com"})
    return resp.json()["id"]


async def test_create_skill(client, user_id):
    resp = await client.post("/skills", json={
        "user_id": user_id, "name": "research", "description": "Web research skill"
    })
    assert resp.status_code == 201
    assert resp.json()["name"] == "research"


async def test_upsert_skill_file(client, user_id):
    skill = await client.post("/skills", json={"user_id": user_id, "name": "s1"})
    skill_id = skill.json()["id"]
    resp = await client.put(f"/skills/{skill_id}/files", json={
        "path": "SKILL.md", "content": "# Research Skill\n..."
    })
    assert resp.status_code == 200
    assert resp.json()["path"] == "SKILL.md"


async def test_list_skill_files(client, user_id):
    skill = await client.post("/skills", json={"user_id": user_id, "name": "s2"})
    skill_id = skill.json()["id"]
    await client.put(f"/skills/{skill_id}/files", json={"path": "SKILL.md", "content": "x"})
    await client.put(f"/skills/{skill_id}/files", json={"path": "scripts/run.sh", "content": "y"})
    resp = await client.get(f"/skills/{skill_id}/files")
    assert len(resp.json()) == 2
```

- [ ] **Step 8.2: Run to verify they fail**

```bash
cd api && pytest tests/test_skills.py -v
```

Expected: 3 errors

- [ ] **Step 8.3: Create models/skill.py**

```python
# api/src/models/skill.py
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class SkillCreate(BaseModel):
    user_id: UUID
    name: str
    description: str = ""


class SkillOut(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    description: str
    created_at: datetime


class SkillFileIn(BaseModel):
    path: str
    content: str


class SkillFileOut(BaseModel):
    id: UUID
    skill_id: UUID
    path: str
    content: str
    updated_at: datetime
```

- [ ] **Step 8.4: Create repositories/skills.py**

```python
# api/src/repositories/skills.py
from uuid import UUID
import asyncpg


class SkillRepo:
    def __init__(self, conn: asyncpg.Connection):
        self._conn = conn

    async def create(self, user_id: UUID, name: str, description: str) -> asyncpg.Record:
        return await self._conn.fetchrow(
            "INSERT INTO skills (user_id, name, description) VALUES ($1, $2, $3) RETURNING *",
            user_id, name, description,
        )

    async def find_by_id(self, skill_id: UUID) -> asyncpg.Record | None:
        return await self._conn.fetchrow("SELECT * FROM skills WHERE id = $1", skill_id)

    async def list_by_user(self, user_id: UUID) -> list[asyncpg.Record]:
        return await self._conn.fetch("SELECT * FROM skills WHERE user_id = $1", user_id)

    async def delete(self, skill_id: UUID) -> None:
        await self._conn.execute("DELETE FROM skills WHERE id = $1", skill_id)


class SkillFileRepo:
    def __init__(self, conn: asyncpg.Connection):
        self._conn = conn

    async def upsert(self, skill_id: UUID, path: str, content: str) -> asyncpg.Record:
        return await self._conn.fetchrow(
            """INSERT INTO skill_files (skill_id, path, content) VALUES ($1, $2, $3)
               ON CONFLICT (skill_id, path)
               DO UPDATE SET content = EXCLUDED.content, updated_at = NOW()
               RETURNING *""",
            skill_id, path, content,
        )

    async def list_by_skill(self, skill_id: UUID) -> list[asyncpg.Record]:
        return await self._conn.fetch(
            "SELECT * FROM skill_files WHERE skill_id = $1 ORDER BY path", skill_id
        )
```

- [ ] **Step 8.5: Create routers/skills.py**

```python
# api/src/routers/skills.py
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from src.db.pool import get_pool
from src.models.skill import SkillCreate, SkillOut, SkillFileIn, SkillFileOut
from src.repositories.skills import SkillRepo, SkillFileRepo

router = APIRouter()


def get_repo(pool=Depends(get_pool)) -> SkillRepo:
    return SkillRepo(pool)


def get_file_repo(pool=Depends(get_pool)) -> SkillFileRepo:
    return SkillFileRepo(pool)


@router.post("", response_model=SkillOut, status_code=201)
async def create_skill(body: SkillCreate, repo: SkillRepo = Depends(get_repo)):
    return dict(await repo.create(body.user_id, body.name, body.description))


@router.get("", response_model=list[SkillOut])
async def list_skills(user_id: UUID, repo: SkillRepo = Depends(get_repo)):
    return [dict(r) for r in await repo.list_by_user(user_id)]


@router.get("/{skill_id}", response_model=SkillOut)
async def get_skill(skill_id: UUID, repo: SkillRepo = Depends(get_repo)):
    record = await repo.find_by_id(skill_id)
    if not record:
        raise HTTPException(404, "Skill not found")
    return dict(record)


@router.delete("/{skill_id}", status_code=204)
async def delete_skill(skill_id: UUID, repo: SkillRepo = Depends(get_repo)):
    if not await repo.find_by_id(skill_id):
        raise HTTPException(404, "Skill not found")
    await repo.delete(skill_id)


@router.put("/{skill_id}/files", response_model=SkillFileOut)
async def upsert_skill_file(
    skill_id: UUID, body: SkillFileIn, repo: SkillFileRepo = Depends(get_file_repo)
):
    return dict(await repo.upsert(skill_id, body.path, body.content))


@router.get("/{skill_id}/files", response_model=list[SkillFileOut])
async def list_skill_files(skill_id: UUID, repo: SkillFileRepo = Depends(get_file_repo)):
    return [dict(r) for r in await repo.list_by_skill(skill_id)]
```

- [ ] **Step 8.6: Run tests**

```bash
cd api && pytest tests/test_skills.py -v
```

Expected: `3 passed`

- [ ] **Step 8.7: Commit**

```bash
git add api/src/models/skill.py api/src/repositories/skills.py api/src/routers/skills.py api/tests/test_skills.py
git commit -m "feat(api): skills + skill_files — CRUD"
```

---

## Task 9: User Envs (Encrypted)

**Files:**
- Create: `api/src/models/env.py`
- Create: `api/src/repositories/envs.py`
- Create: `api/src/routers/envs.py`
- Create: `api/tests/test_envs.py`

- [ ] **Step 9.1: Write the failing tests**

```python
# api/tests/test_envs.py
import pytest


@pytest.fixture
async def user_id(client):
    resp = await client.post("/users", json={"email": "env-owner@example.com"})
    return resp.json()["id"]


async def test_create_env(client, user_id):
    resp = await client.post("/envs", json={
        "user_id": user_id,
        "name": "anthropic",
        "values": {"ANTHROPIC_API_KEY": "sk-ant-test"}
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "anthropic"
    # values must NOT be returned
    assert "values" not in body
    assert "values_encrypted" not in body


async def test_create_env_duplicate_name(client, user_id):
    await client.post("/envs", json={"user_id": user_id, "name": "dupe", "values": {}})
    resp = await client.post("/envs", json={"user_id": user_id, "name": "dupe", "values": {}})
    assert resp.status_code == 409


async def test_list_envs(client, user_id):
    await client.post("/envs", json={"user_id": user_id, "name": "env1", "values": {}})
    await client.post("/envs", json={"user_id": user_id, "name": "env2", "values": {}})
    resp = await client.get(f"/envs?user_id={user_id}")
    assert len(resp.json()) == 2
    for env in resp.json():
        assert "values" not in env


async def test_delete_env(client, user_id):
    create = await client.post("/envs", json={"user_id": user_id, "name": "todel", "values": {}})
    env_id = create.json()["id"]
    assert (await client.delete(f"/envs/{env_id}")).status_code == 204
```

- [ ] **Step 9.2: Run to verify they fail**

```bash
cd api && pytest tests/test_envs.py -v
```

Expected: 4 errors

- [ ] **Step 9.3: Create models/env.py**

```python
# api/src/models/env.py
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class EnvCreate(BaseModel):
    user_id: UUID
    name: str
    values: dict  # written, never read back


class EnvOut(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    created_at: datetime
    # values intentionally omitted
```

- [ ] **Step 9.4: Create repositories/envs.py**

```python
# api/src/repositories/envs.py
from uuid import UUID
import asyncpg
from src.crypto import encrypt_json, decrypt_json


class EnvRepo:
    def __init__(self, conn: asyncpg.Connection):
        self._conn = conn

    async def create(self, user_id: UUID, name: str, values: dict) -> asyncpg.Record:
        encrypted = encrypt_json(values)
        return await self._conn.fetchrow(
            "INSERT INTO user_envs (user_id, name, values_encrypted) VALUES ($1, $2, $3) RETURNING *",
            user_id, name, encrypted,
        )

    async def find_by_id(self, env_id: UUID) -> asyncpg.Record | None:
        return await self._conn.fetchrow("SELECT * FROM user_envs WHERE id = $1", env_id)

    async def list_by_user(self, user_id: UUID) -> list[asyncpg.Record]:
        return await self._conn.fetch("SELECT * FROM user_envs WHERE user_id = $1", user_id)

    async def get_decrypted_values(self, env_id: UUID) -> dict:
        record = await self.find_by_id(env_id)
        if not record:
            raise ValueError(f"Env {env_id} not found")
        return decrypt_json(bytes(record["values_encrypted"]))

    async def delete(self, env_id: UUID) -> None:
        await self._conn.execute("DELETE FROM user_envs WHERE id = $1", env_id)
```

- [ ] **Step 9.5: Create routers/envs.py**

```python
# api/src/routers/envs.py
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
import asyncpg
from src.db.pool import get_pool
from src.models.env import EnvCreate, EnvOut
from src.repositories.envs import EnvRepo

router = APIRouter()


def get_repo(pool=Depends(get_pool)) -> EnvRepo:
    return EnvRepo(pool)


@router.post("", response_model=EnvOut, status_code=201)
async def create_env(body: EnvCreate, repo: EnvRepo = Depends(get_repo)):
    try:
        record = await repo.create(body.user_id, body.name, body.values)
    except asyncpg.UniqueViolationError:
        raise HTTPException(409, "Env name already exists for this user")
    return dict(record)


@router.get("", response_model=list[EnvOut])
async def list_envs(user_id: UUID, repo: EnvRepo = Depends(get_repo)):
    return [dict(r) for r in await repo.list_by_user(user_id)]


@router.delete("/{env_id}", status_code=204)
async def delete_env(env_id: UUID, repo: EnvRepo = Depends(get_repo)):
    if not await repo.find_by_id(env_id):
        raise HTTPException(404, "Env not found")
    await repo.delete(env_id)
```

- [ ] **Step 9.6: Run tests**

```bash
cd api && pytest tests/test_envs.py -v
```

Expected: `4 passed`

- [ ] **Step 9.7: Commit**

```bash
git add api/src/models/env.py api/src/repositories/envs.py api/src/routers/envs.py api/tests/test_envs.py
git commit -m "feat(api): user_envs — encrypted CRUD, values never returned"
```

---

## Task 10: User Channels (Encrypted)

**Files:**
- Create: `api/src/models/channel.py`
- Create: `api/src/repositories/channels.py`
- Create: `api/src/routers/channels.py`
- Create: `api/tests/test_channels.py`

- [ ] **Step 10.1: Write the failing tests**

```python
# api/tests/test_channels.py
import pytest


@pytest.fixture
async def user_id(client):
    resp = await client.post("/users", json={"email": "chan-owner@example.com"})
    return resp.json()["id"]


async def test_create_channel(client, user_id):
    resp = await client.post("/channels", json={
        "user_id": user_id,
        "type": "telegram",
        "config": {"token": "bot:12345", "allow_from": ["111222333"]}
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["type"] == "telegram"
    assert "config" not in body
    assert "config_encrypted" not in body


async def test_list_channels(client, user_id):
    await client.post("/channels", json={"user_id": user_id, "type": "telegram", "config": {}})
    await client.post("/channels", json={"user_id": user_id, "type": "discord", "config": {}})
    resp = await client.get(f"/channels?user_id={user_id}")
    assert len(resp.json()) == 2


async def test_delete_channel(client, user_id):
    create = await client.post("/channels", json={"user_id": user_id, "type": "telegram", "config": {}})
    channel_id = create.json()["id"]
    assert (await client.delete(f"/channels/{channel_id}")).status_code == 204
```

- [ ] **Step 10.2: Run to verify they fail**

```bash
cd api && pytest tests/test_channels.py -v
```

Expected: 3 errors

- [ ] **Step 10.3: Create models/channel.py**

```python
# api/src/models/channel.py
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class ChannelCreate(BaseModel):
    user_id: UUID
    type: str
    config: dict  # written, never returned


class ChannelOut(BaseModel):
    id: UUID
    user_id: UUID
    type: str
    created_at: datetime
    # config intentionally omitted
```

- [ ] **Step 10.4: Create repositories/channels.py**

```python
# api/src/repositories/channels.py
from uuid import UUID
import asyncpg
from src.crypto import encrypt_json, decrypt_json


class ChannelRepo:
    def __init__(self, conn: asyncpg.Connection):
        self._conn = conn

    async def create(self, user_id: UUID, type_: str, config: dict) -> asyncpg.Record:
        encrypted = encrypt_json(config)
        return await self._conn.fetchrow(
            "INSERT INTO user_channels (user_id, type, config_encrypted) VALUES ($1, $2, $3) RETURNING *",
            user_id, type_, encrypted,
        )

    async def find_by_id(self, channel_id: UUID) -> asyncpg.Record | None:
        return await self._conn.fetchrow("SELECT * FROM user_channels WHERE id = $1", channel_id)

    async def list_by_user(self, user_id: UUID) -> list[asyncpg.Record]:
        return await self._conn.fetch("SELECT * FROM user_channels WHERE user_id = $1", user_id)

    async def get_decrypted_config(self, channel_id: UUID) -> dict:
        record = await self.find_by_id(channel_id)
        if not record:
            raise ValueError(f"Channel {channel_id} not found")
        return decrypt_json(bytes(record["config_encrypted"]))

    async def delete(self, channel_id: UUID) -> None:
        await self._conn.execute("DELETE FROM user_channels WHERE id = $1", channel_id)
```

- [ ] **Step 10.5: Create routers/channels.py**

```python
# api/src/routers/channels.py
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from src.db.pool import get_pool
from src.models.channel import ChannelCreate, ChannelOut
from src.repositories.channels import ChannelRepo

router = APIRouter()


def get_repo(pool=Depends(get_pool)) -> ChannelRepo:
    return ChannelRepo(pool)


@router.post("", response_model=ChannelOut, status_code=201)
async def create_channel(body: ChannelCreate, repo: ChannelRepo = Depends(get_repo)):
    record = await repo.create(body.user_id, body.type, body.config)
    return dict(record)


@router.get("", response_model=list[ChannelOut])
async def list_channels(user_id: UUID, repo: ChannelRepo = Depends(get_repo)):
    return [dict(r) for r in await repo.list_by_user(user_id)]


@router.delete("/{channel_id}", status_code=204)
async def delete_channel(channel_id: UUID, repo: ChannelRepo = Depends(get_repo)):
    if not await repo.find_by_id(channel_id):
        raise HTTPException(404, "Channel not found")
    await repo.delete(channel_id)
```

- [ ] **Step 10.6: Run tests**

```bash
cd api && pytest tests/test_channels.py -v
```

Expected: `3 passed`

- [ ] **Step 10.7: Commit**

```bash
git add api/src/models/channel.py api/src/repositories/channels.py api/src/routers/channels.py api/tests/test_channels.py
git commit -m "feat(api): user_channels — encrypted CRUD, config never returned"
```

---

## Task 11: M:M Links + Agent MCP

**Files:**
- Create: `api/src/models/mcp.py`
- Create: `api/src/repositories/mcp.py`
- Create: `api/src/repositories/links.py`
- Create: `api/src/routers/links.py`
- Create: `api/tests/test_links.py`

- [ ] **Step 11.1: Write the failing tests**

```python
# api/tests/test_links.py
import pytest


@pytest.fixture
async def setup(client):
    user = await client.post("/users", json={"email": "links@example.com"})
    uid = user.json()["id"]
    agent = await client.post("/agents", json={"user_id": uid, "name": "Agent"})
    skill = await client.post("/skills", json={"user_id": uid, "name": "research"})
    env = await client.post("/envs", json={"user_id": uid, "name": "anthropic", "values": {"K": "V"}})
    channel = await client.post("/channels", json={"user_id": uid, "type": "telegram", "config": {}})
    return {
        "agent_id": agent.json()["id"],
        "skill_id": skill.json()["id"],
        "env_id": env.json()["id"],
        "channel_id": channel.json()["id"],
    }


async def test_attach_detach_skill(client, setup):
    agent_id, skill_id = setup["agent_id"], setup["skill_id"]
    resp = await client.post(f"/agents/{agent_id}/skills/{skill_id}")
    assert resp.status_code == 204
    links = await client.get(f"/agents/{agent_id}/skills")
    assert any(s["id"] == skill_id for s in links.json())
    resp2 = await client.delete(f"/agents/{agent_id}/skills/{skill_id}")
    assert resp2.status_code == 204


async def test_attach_detach_env(client, setup):
    agent_id, env_id = setup["agent_id"], setup["env_id"]
    await client.post(f"/agents/{agent_id}/envs/{env_id}")
    envs = await client.get(f"/agents/{agent_id}/envs")
    assert any(e["id"] == env_id for e in envs.json())


async def test_add_mcp(client, setup):
    agent_id = setup["agent_id"]
    resp = await client.post(f"/agents/{agent_id}/mcp", json={
        "name": "officeclaw",
        "config": {"url": "http://mcp:8700/mcp", "headers": {"Authorization": "Bearer tok"}}
    })
    assert resp.status_code == 201
    assert resp.json()["name"] == "officeclaw"
    assert "config" not in resp.json()
```

- [ ] **Step 11.2: Run to verify they fail**

```bash
cd api && pytest tests/test_links.py -v
```

Expected: 3 errors

- [ ] **Step 11.3: Create models/mcp.py**

```python
# api/src/models/mcp.py
from uuid import UUID
from pydantic import BaseModel


class McpCreate(BaseModel):
    name: str
    config: dict  # {command, args} or {url, headers} — never returned


class McpOut(BaseModel):
    id: UUID
    agent_id: UUID
    name: str
    # config intentionally omitted
```

- [ ] **Step 11.4: Create repositories/mcp.py**

```python
# api/src/repositories/mcp.py
from uuid import UUID
import asyncpg
from src.crypto import encrypt_json, decrypt_json


class AgentMcpRepo:
    def __init__(self, conn: asyncpg.Connection):
        self._conn = conn

    async def create(self, agent_id: UUID, name: str, config: dict) -> asyncpg.Record:
        return await self._conn.fetchrow(
            """INSERT INTO agent_mcp (agent_id, name, config_encrypted)
               VALUES ($1, $2, $3) RETURNING id, agent_id, name""",
            agent_id, name, encrypt_json(config),
        )

    async def list_by_agent(self, agent_id: UUID) -> list[asyncpg.Record]:
        return await self._conn.fetch(
            "SELECT id, agent_id, name FROM agent_mcp WHERE agent_id = $1", agent_id
        )

    async def get_decrypted_config(self, mcp_id: UUID) -> dict:
        record = await self._conn.fetchrow(
            "SELECT config_encrypted FROM agent_mcp WHERE id = $1", mcp_id
        )
        return decrypt_json(bytes(record["config_encrypted"]))

    async def get_all_decrypted(self, agent_id: UUID) -> list[dict]:
        records = await self._conn.fetch(
            "SELECT name, config_encrypted FROM agent_mcp WHERE agent_id = $1", agent_id
        )
        return [{"name": r["name"], "config": decrypt_json(bytes(r["config_encrypted"]))} for r in records]

    async def delete(self, mcp_id: UUID) -> None:
        await self._conn.execute("DELETE FROM agent_mcp WHERE id = $1", mcp_id)
```

- [ ] **Step 11.5: Create repositories/links.py**

```python
# api/src/repositories/links.py
from uuid import UUID
import asyncpg


class LinkRepo:
    def __init__(self, conn: asyncpg.Connection):
        self._conn = conn

    # Skills
    async def attach_skill(self, agent_id: UUID, skill_id: UUID) -> None:
        await self._conn.execute(
            "INSERT INTO agent_skills (agent_id, skill_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
            agent_id, skill_id,
        )

    async def detach_skill(self, agent_id: UUID, skill_id: UUID) -> None:
        await self._conn.execute(
            "DELETE FROM agent_skills WHERE agent_id = $1 AND skill_id = $2", agent_id, skill_id
        )

    async def list_skills(self, agent_id: UUID) -> list[asyncpg.Record]:
        return await self._conn.fetch(
            "SELECT s.* FROM skills s JOIN agent_skills a ON a.skill_id = s.id WHERE a.agent_id = $1",
            agent_id,
        )

    # Envs
    async def attach_env(self, agent_id: UUID, env_id: UUID) -> None:
        await self._conn.execute(
            "INSERT INTO agent_envs (agent_id, env_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
            agent_id, env_id,
        )

    async def detach_env(self, agent_id: UUID, env_id: UUID) -> None:
        await self._conn.execute(
            "DELETE FROM agent_envs WHERE agent_id = $1 AND env_id = $2", agent_id, env_id
        )

    async def list_envs(self, agent_id: UUID) -> list[asyncpg.Record]:
        return await self._conn.fetch(
            "SELECT e.* FROM user_envs e JOIN agent_envs a ON a.env_id = e.id WHERE a.agent_id = $1",
            agent_id,
        )

    # Channels
    async def attach_channel(self, agent_id: UUID, channel_id: UUID) -> None:
        await self._conn.execute(
            "INSERT INTO agent_channels (agent_id, channel_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
            agent_id, channel_id,
        )

    async def detach_channel(self, agent_id: UUID, channel_id: UUID) -> None:
        await self._conn.execute(
            "DELETE FROM agent_channels WHERE agent_id = $1 AND channel_id = $2", agent_id, channel_id
        )

    async def list_channels(self, agent_id: UUID) -> list[asyncpg.Record]:
        return await self._conn.fetch(
            "SELECT c.* FROM user_channels c JOIN agent_channels a ON a.channel_id = c.id WHERE a.agent_id = $1",
            agent_id,
        )
```

- [ ] **Step 11.6: Create routers/links.py**

```python
# api/src/routers/links.py
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from src.db.pool import get_pool
from src.models.skill import SkillOut
from src.models.env import EnvOut
from src.models.channel import ChannelOut
from src.models.mcp import McpCreate, McpOut
from src.repositories.links import LinkRepo
from src.repositories.mcp import AgentMcpRepo

router = APIRouter(prefix="/agents/{agent_id}")


def get_link_repo(pool=Depends(get_pool)) -> LinkRepo:
    return LinkRepo(pool)


def get_mcp_repo(pool=Depends(get_pool)) -> AgentMcpRepo:
    return AgentMcpRepo(pool)


@router.post("/skills/{skill_id}", status_code=204)
async def attach_skill(agent_id: UUID, skill_id: UUID, repo: LinkRepo = Depends(get_link_repo)):
    await repo.attach_skill(agent_id, skill_id)


@router.delete("/skills/{skill_id}", status_code=204)
async def detach_skill(agent_id: UUID, skill_id: UUID, repo: LinkRepo = Depends(get_link_repo)):
    await repo.detach_skill(agent_id, skill_id)


@router.get("/skills", response_model=list[SkillOut])
async def list_agent_skills(agent_id: UUID, repo: LinkRepo = Depends(get_link_repo)):
    return [dict(r) for r in await repo.list_skills(agent_id)]


@router.post("/envs/{env_id}", status_code=204)
async def attach_env(agent_id: UUID, env_id: UUID, repo: LinkRepo = Depends(get_link_repo)):
    await repo.attach_env(agent_id, env_id)


@router.delete("/envs/{env_id}", status_code=204)
async def detach_env(agent_id: UUID, env_id: UUID, repo: LinkRepo = Depends(get_link_repo)):
    await repo.detach_env(agent_id, env_id)


@router.get("/envs", response_model=list[EnvOut])
async def list_agent_envs(agent_id: UUID, repo: LinkRepo = Depends(get_link_repo)):
    return [dict(r) for r in await repo.list_envs(agent_id)]


@router.post("/channels/{channel_id}", status_code=204)
async def attach_channel(agent_id: UUID, channel_id: UUID, repo: LinkRepo = Depends(get_link_repo)):
    await repo.attach_channel(agent_id, channel_id)


@router.delete("/channels/{channel_id}", status_code=204)
async def detach_channel(agent_id: UUID, channel_id: UUID, repo: LinkRepo = Depends(get_link_repo)):
    await repo.detach_channel(agent_id, channel_id)


@router.get("/channels", response_model=list[ChannelOut])
async def list_agent_channels(agent_id: UUID, repo: LinkRepo = Depends(get_link_repo)):
    return [dict(r) for r in await repo.list_channels(agent_id)]


@router.post("/mcp", response_model=McpOut, status_code=201)
async def add_mcp(agent_id: UUID, body: McpCreate, repo: AgentMcpRepo = Depends(get_mcp_repo)):
    return dict(await repo.create(agent_id, body.name, body.config))


@router.get("/mcp", response_model=list[McpOut])
async def list_mcp(agent_id: UUID, repo: AgentMcpRepo = Depends(get_mcp_repo)):
    return [dict(r) for r in await repo.list_by_agent(agent_id)]
```

- [ ] **Step 11.7: Run tests**

```bash
cd api && pytest tests/test_links.py -v
```

Expected: `3 passed`

- [ ] **Step 11.8: Commit**

```bash
git add api/src/models/mcp.py api/src/repositories/mcp.py api/src/repositories/links.py api/src/routers/links.py api/tests/test_links.py
git commit -m "feat(api): M:M links (agent_skills/envs/channels) + agent_mcp"
```

---

## Task 12: VM Start Payload Builder

**Files:**
- Create: `api/src/vm_payload.py`
- Create: `api/tests/test_vm_payload.py`

Assembles everything needed for `POST sandbox-manager/sandbox/create`: workspace files, skill files, merged env vars, and generated `config.json`.

- [ ] **Step 12.1: Write the failing test**

```python
# api/tests/test_vm_payload.py
import pytest
import json


@pytest.fixture
async def full_agent(client):
    """Create user → agent → files → skill → env → channel → mcp."""
    user = await client.post("/users", json={"email": "payload@example.com"})
    uid = user.json()["id"]

    agent = await client.post("/agents", json={"user_id": uid, "name": "Agent"})
    agent_id = agent.json()["id"]

    await client.put(f"/agents/{agent_id}/files", json={"path": "SOUL.md", "content": "You are helpful."})
    await client.put(f"/agents/{agent_id}/files", json={"path": "AGENTS.md", "content": "# Agents"})

    skill = await client.post("/skills", json={"user_id": uid, "name": "research"})
    skill_id = skill.json()["id"]
    await client.put(f"/skills/{skill_id}/files", json={"path": "SKILL.md", "content": "# Research"})
    await client.post(f"/agents/{agent_id}/skills/{skill_id}")

    env = await client.post("/envs", json={"user_id": uid, "name": "anthropic", "values": {"ANTHROPIC_API_KEY": "sk-test"}})
    await client.post(f"/agents/{agent_id}/envs/{env.json()['id']}")

    channel = await client.post("/channels", json={
        "user_id": uid, "type": "telegram",
        "config": {"token": "bot:999", "allow_from": ["12345"]}
    })
    await client.post(f"/agents/{agent_id}/channels/{channel.json()['id']}")

    await client.post(f"/agents/{agent_id}/mcp", json={
        "name": "officeclaw",
        "config": {"url": "http://mcp:8700/mcp", "headers": {"Authorization": "Bearer tok"}}
    })

    return agent_id


async def test_vm_payload_structure(client, full_agent, raw_pool):
    from src.vm_payload import build_vm_payload
    async with raw_pool.acquire() as conn:
        payload = await build_vm_payload(conn, full_agent)

    # Files
    paths = {f["path"] for f in payload["files"]}
    assert "SOUL.md" in paths
    assert "AGENTS.md" in paths
    assert "skills/research/SKILL.md" in paths

    # Env vars
    assert payload["env"]["ANTHROPIC_API_KEY"] == "sk-test"

    # config.json
    config = json.loads(payload["config_json"])
    assert config["agents"]["defaults"]["workspace"] == "/workspace"
    assert config["providers"]["anthropic"]["apiKey"] == "${ANTHROPIC_API_KEY}"
    assert config["channels"]["telegram"]["token"] == "${TELEGRAM_TOKEN}"
    assert config["tools"]["mcpServers"]["officeclaw"]["url"] == "http://mcp:8700/mcp"
```

- [ ] **Step 12.2: Run to verify it fails**

```bash
cd api && pytest tests/test_vm_payload.py -v
```

Expected: `ImportError` or `ModuleNotFoundError`

- [ ] **Step 12.3: Implement vm_payload.py**

```python
# api/src/vm_payload.py
"""
Assembles the payload sent to sandbox-manager POST /sandbox/create.

Output shape:
{
  "files": [{"path": str, "content": str}],
  "env":   {KEY: VALUE},           # injected as VM env vars
  "config_json": str,              # nanobot config.json content
}
"""
import json
from uuid import UUID
import asyncpg
from src.repositories.agent_files import AgentFileRepo
from src.repositories.links import LinkRepo
from src.repositories.skills import SkillFileRepo
from src.repositories.envs import EnvRepo
from src.repositories.channels import ChannelRepo
from src.repositories.mcp import AgentMcpRepo


async def build_vm_payload(conn: asyncpg.Connection, agent_id: UUID) -> dict:
    file_repo = AgentFileRepo(conn)
    link_repo = LinkRepo(conn)
    env_repo = EnvRepo(conn)
    channel_repo = ChannelRepo(conn)
    mcp_repo = AgentMcpRepo(conn)
    skill_file_repo = SkillFileRepo(conn)

    # 1. Agent workspace files
    files: list[dict] = []
    for rec in await file_repo.list_by_agent(agent_id):
        files.append({"path": rec["path"], "content": rec["content"]})

    # 2. Linked skill files → /workspace/skills/<name>/
    for skill_rec in await link_repo.list_skills(agent_id):
        skill_name = skill_rec["name"]
        for sf in await skill_file_repo.list_by_skill(skill_rec["id"]):
            files.append({
                "path": f"skills/{skill_name}/{sf['path']}",
                "content": sf["content"],
            })

    # 3. Merged env vars from all linked envs
    env_vars: dict = {}
    for env_rec in await link_repo.list_envs(agent_id):
        values = await env_repo.get_decrypted_values(env_rec["id"])
        env_vars.update(values)

    # 4. Build config.json
    config = await _build_config_json(agent_id, conn, env_vars, channel_repo, mcp_repo)

    return {
        "files": files,
        "env": env_vars,
        "config_json": json.dumps(config, indent=2),
    }


async def _build_config_json(
    agent_id: UUID,
    conn: asyncpg.Connection,
    env_vars: dict,
    channel_repo: ChannelRepo,
    mcp_repo: AgentMcpRepo,
) -> dict:
    link_repo = LinkRepo(conn)

    # Providers: one entry per known key prefix found in env_vars
    providers: dict = {}
    if any(k.startswith("ANTHROPIC") for k in env_vars):
        providers["anthropic"] = {"apiKey": "${ANTHROPIC_API_KEY}"}
    if any(k.startswith("OPENAI") for k in env_vars):
        providers["openai"] = {"apiKey": "${OPENAI_API_KEY}"}
    if any(k.startswith("OPENROUTER") for k in env_vars):
        providers["openrouter"] = {"apiKey": "${OPENROUTER_API_KEY}"}
    if any(k.startswith("GROQ") for k in env_vars):
        providers["groq"] = {"apiKey": "${GROQ_API_KEY}"}

    # Channels
    channels_config: dict = {"sendProgress": True}
    for ch_rec in await link_repo.list_channels(agent_id):
        cfg = await channel_repo.get_decrypted_config(ch_rec["id"])
        ch_type = ch_rec["type"]
        if ch_type == "telegram":
            token_key = "TELEGRAM_TOKEN"
            env_vars.setdefault(token_key, cfg.get("token", ""))
            channels_config["telegram"] = {
                "enabled": True,
                "token": f"${{{token_key}}}",
                "allowFrom": cfg.get("allow_from", []),
            }
        elif ch_type == "discord":
            token_key = "DISCORD_TOKEN"
            env_vars.setdefault(token_key, cfg.get("token", ""))
            channels_config["discord"] = {
                "enabled": True,
                "token": f"${{{token_key}}}",
                "allowFrom": cfg.get("allow_from", []),
            }

    # MCP servers
    mcp_servers: dict = {}
    for mcp in await mcp_repo.get_all_decrypted(agent_id):
        mcp_servers[mcp["name"]] = mcp["config"]

    return {
        "agents": {
            "defaults": {
                "workspace": "/workspace",
                "model": "anthropic/claude-sonnet-4-6",
            }
        },
        "providers": providers,
        "channels": channels_config,
        "tools": {
            "exec": {"enable": True},
            "mcpServers": mcp_servers,
        },
        "gateway": {"host": "0.0.0.0", "port": 18790},
    }
```

- [ ] **Step 12.4: Run tests**

```bash
cd api && pytest tests/test_vm_payload.py -v
```

Expected: `1 passed`

- [ ] **Step 12.5: Run full test suite**

```bash
cd api && pytest --cov=src --cov-report=term-missing -v
```

Expected: all tests pass, coverage ≥ 80%

- [ ] **Step 12.6: Commit**

```bash
git add api/src/vm_payload.py api/tests/test_vm_payload.py
git commit -m "feat(api): vm_payload builder — assembles sandbox-manager start payload"
```

---

## Self-Review Notes

- All 12 tasks map directly to spec sections: DB schema ✓, file storage ✓, secrets ✓, vm start sequence ✓
- No TBDs or TODOs in any step
- Types are consistent: `UUID` throughout, `asyncpg.Record` returned from repos and converted with `dict(record)` in routers
- `SkillFileRepo` is used in both `routers/skills.py` (Task 8) and `vm_payload.py` (Task 12) — same class, consistent
- `get_decrypted_values` / `get_decrypted_config` / `get_all_decrypted` naming is consistent across envs, channels, mcp repos
- `EnvOut`, `ChannelOut`, `McpOut` intentionally omit encrypted fields — tested explicitly
- `LinkRepo.list_envs` returns `user_envs` records (without values) — safe to expose in `/agents/{id}/envs`
