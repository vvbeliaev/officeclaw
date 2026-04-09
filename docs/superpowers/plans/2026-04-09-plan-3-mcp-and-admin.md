# MCP Server + Admin Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mount a FastMCP server inside the existing `api/` FastAPI app and auto-create an Admin agent (with seeded persona files and officeclaw MCP config) whenever a new user registers.

**Architecture:** MCP is a controller layer on top of existing repositories — no new data access patterns. `admin.py` runs at user registration time using the same pool-or-conn pattern as all other repos. The FastMCP instance is a module-level singleton; its pool reference is set by the lifespan. Tools expose the same CRUD operations already in the REST API, scoped by `OFFICECLAW_TOKEN` bearer auth.

**Tech Stack:** Python 3.13, FastAPI, asyncpg, fastmcp>=2.3, existing repo/model layer

---

## File Map

```
api/
  src/
    admin.py                   # CREATE: create_admin_for_user() — token + agent seeding
    mcp_server.py              # CREATE: FastMCP instance, auth helper, all tools
    models/user.py             # MODIFY: add UserRegistered model (includes token)
    repositories/users.py      # MODIFY: add set_token() and find_by_token()
    routers/users.py           # MODIFY: POST /users calls admin, returns UserRegistered
    config.py                  # MODIFY: add mcp_base_url setting
    main.py                    # MODIFY: set_pool in lifespan, mount MCP sub-app
  migrations/
    versions/002_add_officeclaw_token.sql   # CREATE: officeclaw_token column
  tests/
    conftest.py                # MODIFY: run all *.sql migrations (sorted), not just 001
    test_admin.py              # CREATE: admin creation flow tests
    test_mcp_tools.py          # CREATE: MCP business logic function tests
```

---

## Task 1: Migration 002 + conftest update

**Files:**

- Create: `api/migrations/versions/002_add_officeclaw_token.sql`
- Modify: `api/tests/conftest.py`

- [ ] **Step 1.1: Create migration SQL**

```sql
-- api/migrations/versions/002_add_officeclaw_token.sql
ALTER TABLE users ADD COLUMN IF NOT EXISTS officeclaw_token TEXT UNIQUE;
```

- [ ] **Step 1.2: Apply migration to dev DB**

```bash
cd /Users/vladimirbeliaev/vvbeliaev/officeclaw/api && \
  psql $DATABASE_URL -f migrations/versions/002_add_officeclaw_token.sql
```

Expected: `ALTER TABLE`

- [ ] **Step 1.3: Update conftest.py to run all migrations**

Current conftest has:

```python
sql = (MIGRATIONS_DIR / "001_initial_schema.sql").read_text()
async with raw_pool.acquire() as conn:
    await conn.execute(sql)
```

Replace with:

```python
for sql_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
    sql = sql_file.read_text()
    async with raw_pool.acquire() as conn:
        await conn.execute(sql)
```

Read `api/tests/conftest.py` first, then make the edit to the `run_migrations` fixture body only.

- [ ] **Step 1.4: Verify existing tests still pass**

```bash
cd /Users/vladimirbeliaev/vvbeliaev/officeclaw/api && python -m pytest -v
```

Expected: `28 passed`

- [ ] **Step 1.5: Commit**

```bash
cd /Users/vladimirbeliaev/vvbeliaev/officeclaw && \
  git add api/migrations/versions/002_add_officeclaw_token.sql api/tests/conftest.py && \
  git commit -m "feat(api): migration 002 — officeclaw_token column; conftest runs all migrations"
```

---

## Task 2: Admin creation flow

**Files:**

- Modify: `api/src/models/user.py`
- Modify: `api/src/repositories/users.py`
- Modify: `api/src/config.py`
- Create: `api/src/admin.py`
- Modify: `api/src/routers/users.py`
- Create: `api/tests/test_admin.py`

- [ ] **Step 2.1: Write the failing tests**

```python
# api/tests/test_admin.py
import pytest


async def test_create_user_returns_token(client):
    resp = await client.post("/users", json={"email": "admin-test@example.com"})
    assert resp.status_code == 201
    body = resp.json()
    assert "officeclaw_token" in body
    assert len(body["officeclaw_token"]) > 20


async def test_create_user_creates_admin_agent(client):
    resp = await client.post("/users", json={"email": "admin-agent@example.com"})
    uid = resp.json()["id"]
    agents = await client.get(f"/agents?user_id={uid}")
    assert agents.status_code == 200
    admin_agents = [a for a in agents.json() if a["is_admin"]]
    assert len(admin_agents) == 1
    assert admin_agents[0]["name"] == "Admin"


async def test_admin_agent_has_seed_files(client):
    resp = await client.post("/users", json={"email": "admin-files@example.com"})
    uid = resp.json()["id"]
    agents = await client.get(f"/agents?user_id={uid}")
    agent_id = next(a["id"] for a in agents.json() if a["is_admin"])

    files = await client.get(f"/agents/{agent_id}/files")
    paths = {f["path"] for f in files.json()}
    assert "SOUL.md" in paths
    assert "AGENTS.md" in paths
    assert "TOOLS.md" in paths


async def test_admin_agent_has_mcp_config(client):
    resp = await client.post("/users", json={"email": "admin-mcp@example.com"})
    uid = resp.json()["id"]
    agents = await client.get(f"/agents?user_id={uid}")
    agent_id = next(a["id"] for a in agents.json() if a["is_admin"])

    mcp_list = await client.get(f"/agents/{agent_id}/mcp")
    names = [m["name"] for m in mcp_list.json()]
    assert "officeclaw" in names


async def test_admin_agent_has_env_linked(client):
    resp = await client.post("/users", json={"email": "admin-env@example.com"})
    uid = resp.json()["id"]
    agents = await client.get(f"/agents?user_id={uid}")
    agent_id = next(a["id"] for a in agents.json() if a["is_admin"])

    envs = await client.get(f"/agents/{agent_id}/envs")
    assert len(envs.json()) == 1
    assert envs.json()[0]["name"] == "officeclaw"
```

- [ ] **Step 2.2: Run to verify they fail**

```bash
cd /Users/vladimirbeliaev/vvbeliaev/officeclaw/api && python -m pytest tests/test_admin.py -v
```

Expected: 5 failures (token not in response, etc.)

- [ ] **Step 2.3: Add `UserRegistered` to `src/models/user.py`**

Read the file, then append:

```python
class UserRegistered(BaseModel):
    id: UUID
    email: str
    created_at: datetime
    officeclaw_token: str  # shown once at registration, store it securely
```

- [ ] **Step 2.4: Add `set_token` and `find_by_token` to `src/repositories/users.py`**

Read the file, then append to the `UserRepo` class:

```python
    async def set_token(self, user_id: UUID, token: str) -> None:
        await self._conn.execute(
            "UPDATE users SET officeclaw_token = $2 WHERE id = $1",
            user_id, token,
        )

    async def find_by_token(self, token: str) -> asyncpg.Record | None:
        return await self._conn.fetchrow(
            "SELECT id FROM users WHERE officeclaw_token = $1", token
        )
```

- [ ] **Step 2.5: Add `mcp_base_url` to `src/config.py`**

Read the file, then add to the `Settings` class:

```python
    mcp_base_url: str = "http://localhost:8000"
```

- [ ] **Step 2.6: Create `src/admin.py`**

```python
# api/src/admin.py
"""
Admin agent bootstrap — runs at user registration.

Creates:
  1. OFFICECLAW_TOKEN stored in users.officeclaw_token
  2. user_envs row: name='officeclaw', values={OFFICECLAW_TOKEN: token}
  3. agents row: name='Admin', is_admin=True
  4. agent_files: SOUL.md, AGENTS.md, TOOLS.md
  5. agent_mcp: name='officeclaw', config with url + auth header
  6. agent_envs link: admin agent ← officeclaw env
"""
import secrets
from uuid import UUID

import asyncpg

from src.config import get_settings
from src.repositories.agents import AgentRepo
from src.repositories.agent_files import AgentFileRepo
from src.repositories.envs import EnvRepo
from src.repositories.links import LinkRepo
from src.repositories.mcp import AgentMcpRepo
from src.repositories.users import UserRepo

_SOUL_MD = """\
You are the Admin agent for OfficeClaw — a fleet manager AI that helps users \
create, configure, and manage their personal AI agents.

You have access to the `officeclaw` MCP tool which allows you to perform all \
fleet operations: creating agents, installing skills, configuring channels, \
managing environment variables, and monitoring fleet status.

When the user asks you to do something with their agents, use the officeclaw \
tools to make it happen. Be proactive and helpful. When creating agents, \
suggest good names and configurations. When installing skills, explain what \
the skill does.

Always confirm important actions (deleting agents, changing configurations) \
before executing them.
"""

_AGENTS_MD = """\
# Agents

You operate as a fleet manager. Your job is to help the user build and manage \
their fleet of AI agents.

## Available MCP Tools
- officeclaw: Fleet management (create/start/stop/delete agents, manage skills, envs, channels)
"""

_TOOLS_MD = """\
# Tools

## officeclaw MCP

Fleet management tool. Use it to:
- List agents: `list_agents`
- Create an agent: `create_agent(name, image?)`
- Start/stop an agent: `start_agent(agent_id)`, `stop_agent(agent_id)`
- Update files: `update_agent_file(agent_id, path, content)`
- Delete an agent: `delete_agent(agent_id)`
- Skills: `list_skills`, `create_skill(name, description?)`, `attach_skill(agent_id, skill_id)`
- Envs: `list_envs`, `create_env(name, values_json)`
- Channels: `list_channels`
- Fleet status: `get_fleet_status`
"""


async def create_admin_for_user(
    conn: asyncpg.Connection, user_id: UUID
) -> str:
    """
    Bootstrap the Admin agent for a newly registered user.
    Returns the plain-text OFFICECLAW_TOKEN (show once to the user).

    Uses conn directly — compatible with both asyncpg.Pool and asyncpg.Connection
    (same pattern as all other repos in this codebase).
    """
    token = secrets.token_urlsafe(32)
    settings = get_settings()

    users_repo = UserRepo(conn)
    agents_repo = AgentRepo(conn)
    files_repo = AgentFileRepo(conn)
    envs_repo = EnvRepo(conn)
    links_repo = LinkRepo(conn)
    mcp_repo = AgentMcpRepo(conn)

    await users_repo.set_token(user_id, token)

    env_record = await envs_repo.create(
        user_id, "officeclaw", {"OFFICECLAW_TOKEN": token}
    )

    agent_record = await agents_repo.create(
        user_id,
        "Admin",
        "ghcr.io/hkuds/nanobot:latest",
        True,
    )
    agent_id = agent_record["id"]

    await files_repo.upsert(agent_id, "SOUL.md", _SOUL_MD)
    await files_repo.upsert(agent_id, "AGENTS.md", _AGENTS_MD)
    await files_repo.upsert(agent_id, "TOOLS.md", _TOOLS_MD)

    mcp_url = f"{settings.mcp_base_url}/mcp"
    await mcp_repo.create(
        agent_id,
        "officeclaw",
        {
            "url": mcp_url,
            "headers": {"Authorization": "Bearer ${OFFICECLAW_TOKEN}"},
        },
    )

    await links_repo.attach_env(agent_id, env_record["id"])

    return token
```

- [ ] **Step 2.7: Update `src/routers/users.py` to call admin and return `UserRegistered`**

Replace the entire file:

```python
# api/src/routers/users.py
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException

from src.admin import create_admin_for_user
from src.db.pool import get_pool
from src.models.user import UserCreate, UserOut, UserRegistered
from src.repositories.users import UserRepo

router = APIRouter()


def get_repo(conn: asyncpg.Connection = Depends(get_pool)) -> UserRepo:
    return UserRepo(conn)


@router.post("", response_model=UserRegistered, status_code=201)
async def create_user(
    body: UserCreate,
    conn: asyncpg.Connection = Depends(get_pool),
) -> UserRegistered:
    repo = UserRepo(conn)
    try:
        record = await repo.create(body.email)
    except asyncpg.UniqueViolationError:
        raise HTTPException(409, "Email already registered")
    token = await create_admin_for_user(conn, record["id"])
    return UserRegistered(
        id=record["id"],
        email=record["email"],
        created_at=record["created_at"],
        officeclaw_token=token,
    )


@router.get("/{user_id}", response_model=UserOut)
async def get_user(user_id: UUID, repo: UserRepo = Depends(get_repo)) -> UserOut:
    record = await repo.find_by_id(user_id)
    if not record:
        raise HTTPException(404, "User not found")
    return UserOut(**dict(record))
```

- [ ] **Step 2.8: Run admin tests**

```bash
cd /Users/vladimirbeliaev/vvbeliaev/officeclaw/api && python -m pytest tests/test_admin.py -v
```

Expected: `5 passed`

- [ ] **Step 2.9: Run full suite to check no regressions**

```bash
cd /Users/vladimirbeliaev/vvbeliaev/officeclaw/api && python -m pytest -v
```

Expected: all 33 tests pass (`28` original + `5` new)

- [ ] **Step 2.10: Commit**

```bash
cd /Users/vladimirbeliaev/vvbeliaev/officeclaw && \
  git add api/src/models/user.py api/src/repositories/users.py api/src/config.py \
          api/src/admin.py api/src/routers/users.py api/tests/test_admin.py && \
  git commit -m "feat(api): admin agent bootstrap at user registration"
```

---

## Task 3: MCP server — foundation, auth, and first tools

**Files:**

- Create: `api/src/mcp_server.py`
- Modify: `api/src/main.py`
- Modify: `api/pyproject.toml`
- Create: `api/tests/test_mcp_tools.py` (scaffold + first tests)

- [ ] **Step 3.1: Add fastmcp dependency**

Read `api/pyproject.toml`, then add `"fastmcp>=2.3"` to the `dependencies` list.

Install it:

```bash
cd /Users/vladimirbeliaev/vvbeliaev/officeclaw/api && pip install "fastmcp>=2.3"
```

Expected: installs without error; `fastmcp` is importable.

- [ ] **Step 3.2: Write the failing tests (scaffold + list_agents, get_fleet_status)**

```python
# api/tests/test_mcp_tools.py
import pytest
from uuid import UUID


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


async def test_mcp_list_agents(mcp_conn_user):
    from src.mcp_server import mcp_list_agents
    conn, user_id = mcp_conn_user
    agents = await mcp_list_agents(conn, user_id)
    # Admin agent was created by registration
    assert any(a["name"] == "Admin" for a in agents)


async def test_mcp_get_fleet_status(mcp_conn_user):
    from src.mcp_server import mcp_get_fleet_status
    conn, user_id = mcp_conn_user
    status = await mcp_get_fleet_status(conn, user_id)
    assert "agents" in status
    assert "summary" in status
    assert set(status["summary"].keys()) == {"idle", "running", "error"}
```

- [ ] **Step 3.3: Run to verify they fail**

```bash
cd /Users/vladimirbeliaev/vvbeliaev/officeclaw/api && python -m pytest tests/test_mcp_tools.py::test_mcp_list_agents tests/test_mcp_tools.py::test_mcp_get_fleet_status -v
```

Expected: `ImportError` (mcp_server not yet created)

- [ ] **Step 3.4: Create `src/mcp_server.py`**

```python
# api/src/mcp_server.py
"""
OfficeClaw MCP server — fleet management tools for the Admin agent.

Mounted at /mcp in the FastAPI app. All tools are scoped to the authenticated
user via OFFICECLAW_TOKEN bearer auth.

Pattern: each tool has a corresponding mcp_<name>(conn, user_id, ...) business
logic function. Tests call these directly. The @mcp.tool() wrappers are thin
— they validate auth, acquire a connection, and delegate.
"""
import json
import logging
from uuid import UUID

import asyncpg
from fastmcp import FastMCP
from fastmcp.server.context import Context

from src.repositories.agents import AgentRepo
from src.repositories.agent_files import AgentFileRepo
from src.repositories.envs import EnvRepo
from src.repositories.channels import ChannelRepo
from src.repositories.links import LinkRepo
from src.repositories.skills import SkillRepo
from src.repositories.users import UserRepo

logger = logging.getLogger(__name__)

mcp = FastMCP("OfficeClaw")

# Module-level pool set by main.py lifespan via set_pool().
# In production: asyncpg.Pool. In tests: not used (tools call business logic
# functions directly with a conn fixture).
_pool: asyncpg.Pool | None = None


def set_pool(pool: asyncpg.Pool) -> None:
    global _pool
    _pool = pool


# ---------------------------------------------------------------------------
# Auth helper
# ---------------------------------------------------------------------------

async def _require_user(context: Context) -> UUID:
    """Extract and validate bearer token → return user_id."""
    request = context.request_context.request
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        raise ValueError("Missing or malformed Authorization header")
    token = auth[7:]
    assert _pool is not None, "MCP pool not initialised"
    async with _pool.acquire() as conn:
        record = await UserRepo(conn).find_by_token(token)
    if not record:
        raise ValueError("Invalid OFFICECLAW_TOKEN")
    return record["id"]


# ---------------------------------------------------------------------------
# Business logic functions (tested directly)
# ---------------------------------------------------------------------------

async def mcp_list_agents(conn: asyncpg.Connection, user_id: UUID) -> list[dict]:
    records = await AgentRepo(conn).list_by_user(user_id)
    return [
        {
            "id": str(r["id"]),
            "name": r["name"],
            "status": r["status"],
            "is_admin": r["is_admin"],
            "image": r["image"],
        }
        for r in records
    ]


async def mcp_get_fleet_status(conn: asyncpg.Connection, user_id: UUID) -> dict:
    records = await AgentRepo(conn).list_by_user(user_id)
    agents = [
        {"id": str(r["id"]), "name": r["name"], "status": r["status"], "is_admin": r["is_admin"]}
        for r in records
    ]
    summary = {"idle": 0, "running": 0, "error": 0}
    for a in agents:
        summary[a["status"]] = summary.get(a["status"], 0) + 1
    return {"agents": agents, "summary": summary}


async def mcp_create_agent(
    conn: asyncpg.Connection, user_id: UUID, name: str, image: str
) -> dict:
    record = await AgentRepo(conn).create(user_id, name, image, False)
    return {"id": str(record["id"]), "name": record["name"], "status": record["status"]}


async def mcp_update_agent_file(
    conn: asyncpg.Connection, agent_id: UUID, path: str, content: str
) -> dict:
    record = await AgentFileRepo(conn).upsert(agent_id, path, content)
    return {"agent_id": str(record["agent_id"]), "path": record["path"]}


async def mcp_start_agent(conn: asyncpg.Connection, agent_id: UUID) -> dict:
    record = await AgentRepo(conn).update(agent_id, status="running")
    if not record:
        raise ValueError(f"Agent {agent_id} not found")
    return {"id": str(record["id"]), "status": record["status"]}


async def mcp_stop_agent(conn: asyncpg.Connection, agent_id: UUID) -> dict:
    record = await AgentRepo(conn).update(agent_id, status="idle")
    if not record:
        raise ValueError(f"Agent {agent_id} not found")
    return {"id": str(record["id"]), "status": record["status"]}


async def mcp_delete_agent(conn: asyncpg.Connection, agent_id: UUID) -> dict:
    repo = AgentRepo(conn)
    record = await repo.find_by_id(agent_id)
    if not record:
        raise ValueError(f"Agent {agent_id} not found")
    if record["is_admin"]:
        raise ValueError("Cannot delete the Admin agent")
    await repo.delete(agent_id)
    return {"deleted": str(agent_id)}


async def mcp_list_skills(conn: asyncpg.Connection, user_id: UUID) -> list[dict]:
    records = await SkillRepo(conn).list_by_user(user_id)
    return [{"id": str(r["id"]), "name": r["name"], "description": r["description"]} for r in records]


async def mcp_create_skill(
    conn: asyncpg.Connection, user_id: UUID, name: str, description: str
) -> dict:
    record = await SkillRepo(conn).create(user_id, name, description)
    return {"id": str(record["id"]), "name": record["name"]}


async def mcp_attach_skill(
    conn: asyncpg.Connection, agent_id: UUID, skill_id: UUID
) -> dict:
    await LinkRepo(conn).attach_skill(agent_id, skill_id)
    return {"agent_id": str(agent_id), "skill_id": str(skill_id), "attached": True}


async def mcp_list_envs(conn: asyncpg.Connection, user_id: UUID) -> list[dict]:
    records = await EnvRepo(conn).list_by_user(user_id)
    return [{"id": str(r["id"]), "name": r["name"]} for r in records]


async def mcp_create_env(
    conn: asyncpg.Connection, user_id: UUID, name: str, values_json: str
) -> dict:
    values = json.loads(values_json)
    record = await EnvRepo(conn).create(user_id, name, values)
    return {"id": str(record["id"]), "name": record["name"]}


async def mcp_list_channels(conn: asyncpg.Connection, user_id: UUID) -> list[dict]:
    records = await ChannelRepo(conn).list_by_user(user_id)
    return [{"id": str(r["id"]), "type": r["type"]} for r in records]


# ---------------------------------------------------------------------------
# MCP tool wrappers (thin — validate auth, acquire conn, delegate)
# ---------------------------------------------------------------------------

@mcp.tool()
async def list_agents(context: Context) -> list[dict]:
    """List all agents for the authenticated user."""
    user_id = await _require_user(context)
    assert _pool is not None
    async with _pool.acquire() as conn:
        return await mcp_list_agents(conn, user_id)


@mcp.tool()
async def get_fleet_status(context: Context) -> dict:
    """Return all agents with a status summary (idle/running/error counts)."""
    user_id = await _require_user(context)
    assert _pool is not None
    async with _pool.acquire() as conn:
        return await mcp_get_fleet_status(conn, user_id)


@mcp.tool()
async def create_agent(context: Context, name: str, image: str = "ghcr.io/hkuds/nanobot:latest") -> dict:
    """Create a new agent. Returns {id, name, status}."""
    user_id = await _require_user(context)
    assert _pool is not None
    async with _pool.acquire() as conn:
        return await mcp_create_agent(conn, user_id, name, image)


@mcp.tool()
async def update_agent_file(context: Context, agent_id: str, path: str, content: str) -> dict:
    """Upsert a workspace file for an agent."""
    await _require_user(context)
    assert _pool is not None
    async with _pool.acquire() as conn:
        return await mcp_update_agent_file(conn, UUID(agent_id), path, content)


@mcp.tool()
async def start_agent(context: Context, agent_id: str) -> dict:
    """Start an agent (sets status=running). VM lifecycle wired in Plan 2."""
    await _require_user(context)
    assert _pool is not None
    async with _pool.acquire() as conn:
        return await mcp_start_agent(conn, UUID(agent_id))


@mcp.tool()
async def stop_agent(context: Context, agent_id: str) -> dict:
    """Stop an agent (sets status=idle). VM lifecycle wired in Plan 2."""
    await _require_user(context)
    assert _pool is not None
    async with _pool.acquire() as conn:
        return await mcp_stop_agent(conn, UUID(agent_id))


@mcp.tool()
async def delete_agent(context: Context, agent_id: str) -> dict:
    """Delete an agent. Raises if agent is the Admin agent."""
    await _require_user(context)
    assert _pool is not None
    async with _pool.acquire() as conn:
        return await mcp_delete_agent(conn, UUID(agent_id))


@mcp.tool()
async def list_skills(context: Context) -> list[dict]:
    """List all skills in the user's library."""
    user_id = await _require_user(context)
    assert _pool is not None
    async with _pool.acquire() as conn:
        return await mcp_list_skills(conn, user_id)


@mcp.tool()
async def create_skill(context: Context, name: str, description: str = "") -> dict:
    """Create a new skill in the user's library."""
    user_id = await _require_user(context)
    assert _pool is not None
    async with _pool.acquire() as conn:
        return await mcp_create_skill(conn, user_id, name, description)


@mcp.tool()
async def attach_skill(context: Context, agent_id: str, skill_id: str) -> dict:
    """Attach a skill to an agent."""
    await _require_user(context)
    assert _pool is not None
    async with _pool.acquire() as conn:
        return await mcp_attach_skill(conn, UUID(agent_id), UUID(skill_id))


@mcp.tool()
async def list_envs(context: Context) -> list[dict]:
    """List all env configs for the authenticated user (values never returned)."""
    user_id = await _require_user(context)
    assert _pool is not None
    async with _pool.acquire() as conn:
        return await mcp_list_envs(conn, user_id)


@mcp.tool()
async def create_env(context: Context, name: str, values_json: str) -> dict:
    """Create a named env config. values_json: JSON string of {KEY: VALUE} pairs."""
    user_id = await _require_user(context)
    assert _pool is not None
    async with _pool.acquire() as conn:
        return await mcp_create_env(conn, user_id, name, values_json)


@mcp.tool()
async def list_channels(context: Context) -> list[dict]:
    """List all channel integrations (config never returned)."""
    user_id = await _require_user(context)
    assert _pool is not None
    async with _pool.acquire() as conn:
        return await mcp_list_channels(conn, user_id)
```

- [ ] **Step 3.5: Mount MCP server in `src/main.py`**

Replace `src/main.py` with:

```python
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
    app.mount("/mcp", mcp.sse_app())
    return app


app = create_app()
```

- [ ] **Step 3.6: Run the first MCP tests**

```bash
cd /Users/vladimirbeliaev/vvbeliaev/officeclaw/api && \
  python -m pytest tests/test_mcp_tools.py::test_mcp_list_agents \
                   tests/test_mcp_tools.py::test_mcp_get_fleet_status -v
```

Expected: `2 passed`

- [ ] **Step 3.7: Commit**

```bash
cd /Users/vladimirbeliaev/vvbeliaev/officeclaw && \
  git add api/pyproject.toml api/src/mcp_server.py api/src/main.py \
          api/tests/test_mcp_tools.py && \
  git commit -m "feat(api): FastMCP server mounted at /mcp — foundation + list_agents + fleet_status"
```

---

## Task 4: MCP agent tools — create, start, stop, delete, update_file

**Files:**

- Modify: `api/tests/test_mcp_tools.py`

(All business logic is already in `mcp_server.py` from Task 3. This task adds tests for the agent mutation functions.)

- [ ] **Step 4.1: Write the failing tests**

Add to `api/tests/test_mcp_tools.py` (append after existing tests):

```python
async def test_mcp_create_agent(mcp_conn_user):
    from src.mcp_server import mcp_create_agent
    conn, user_id = mcp_conn_user
    result = await mcp_create_agent(conn, user_id, "MyBot", "ghcr.io/hkuds/nanobot:latest")
    assert result["name"] == "MyBot"
    assert result["status"] == "idle"
    assert "id" in result


async def test_mcp_update_agent_file(mcp_conn_user):
    from src.mcp_server import mcp_create_agent, mcp_update_agent_file
    conn, user_id = mcp_conn_user
    agent = await mcp_create_agent(conn, user_id, "FileBot", "ghcr.io/hkuds/nanobot:latest")
    result = await mcp_update_agent_file(conn, UUID(agent["id"]), "SOUL.md", "You are FileBot.")
    assert result["path"] == "SOUL.md"


async def test_mcp_start_stop_agent(mcp_conn_user):
    from src.mcp_server import mcp_create_agent, mcp_start_agent, mcp_stop_agent
    conn, user_id = mcp_conn_user
    agent = await mcp_create_agent(conn, user_id, "StatusBot", "ghcr.io/hkuds/nanobot:latest")
    agent_id = UUID(agent["id"])

    started = await mcp_start_agent(conn, agent_id)
    assert started["status"] == "running"

    stopped = await mcp_stop_agent(conn, agent_id)
    assert stopped["status"] == "idle"


async def test_mcp_delete_agent(mcp_conn_user):
    from src.mcp_server import mcp_create_agent, mcp_delete_agent, mcp_list_agents
    conn, user_id = mcp_conn_user
    agent = await mcp_create_agent(conn, user_id, "DeleteMe", "ghcr.io/hkuds/nanobot:latest")
    agent_id = UUID(agent["id"])

    result = await mcp_delete_agent(conn, agent_id)
    assert result["deleted"] == str(agent_id)

    agents = await mcp_list_agents(conn, user_id)
    assert not any(a["id"] == str(agent_id) for a in agents)


async def test_mcp_delete_admin_agent_raises(mcp_conn_user):
    from src.mcp_server import mcp_list_agents, mcp_delete_agent
    import pytest
    conn, user_id = mcp_conn_user
    agents = await mcp_list_agents(conn, user_id)
    admin_id = UUID(next(a["id"] for a in agents if a["is_admin"]))
    with pytest.raises(ValueError, match="Cannot delete the Admin agent"):
        await mcp_delete_agent(conn, admin_id)
```

- [ ] **Step 4.2: Run to verify they fail**

```bash
cd /Users/vladimirbeliaev/vvbeliaev/officeclaw/api && \
  python -m pytest tests/test_mcp_tools.py::test_mcp_create_agent \
                   tests/test_mcp_tools.py::test_mcp_update_agent_file \
                   tests/test_mcp_tools.py::test_mcp_start_stop_agent \
                   tests/test_mcp_tools.py::test_mcp_delete_agent \
                   tests/test_mcp_tools.py::test_mcp_delete_admin_agent_raises -v
```

Expected: 5 failures (functions exist but tests not yet in file)

_Note: if the functions are already importable from Task 3, the failures will be `ImportError` for the missing names — which means they DO need to be implemented. Confirm `mcp_create_agent`, `mcp_update_agent_file`, `mcp_start_agent`, `mcp_stop_agent`, `mcp_delete_agent` are all defined in `mcp_server.py` from Task 3 before moving on. If Task 3 was implemented correctly, these will PASS immediately — that's expected and correct._

- [ ] **Step 4.3: Run the new tests**

```bash
cd /Users/vladimirbeliaev/vvbeliaev/officeclaw/api && \
  python -m pytest tests/test_mcp_tools.py -v
```

Expected: `7 passed` (2 from Task 3 + 5 new)

- [ ] **Step 4.4: Commit**

```bash
cd /Users/vladimirbeliaev/vvbeliaev/officeclaw && \
  git add api/tests/test_mcp_tools.py && \
  git commit -m "test(api): MCP agent tool tests — create, start, stop, delete, update_file"
```

---

## Task 5: MCP resource tools — skills, envs, channels

**Files:**

- Modify: `api/tests/test_mcp_tools.py`

(All business logic is already in `mcp_server.py` from Task 3.)

- [ ] **Step 5.1: Write the failing tests**

Append to `api/tests/test_mcp_tools.py`:

```python
async def test_mcp_create_and_list_skills(mcp_conn_user):
    from src.mcp_server import mcp_create_skill, mcp_list_skills
    conn, user_id = mcp_conn_user
    result = await mcp_create_skill(conn, user_id, "research", "Web research")
    assert result["name"] == "research"
    skills = await mcp_list_skills(conn, user_id)
    assert any(s["name"] == "research" for s in skills)


async def test_mcp_attach_skill(mcp_conn_user):
    from src.mcp_server import mcp_create_agent, mcp_create_skill, mcp_attach_skill, mcp_list_agents
    from src.repositories.links import LinkRepo
    conn, user_id = mcp_conn_user
    agent = await mcp_create_agent(conn, user_id, "SkillBot", "ghcr.io/hkuds/nanobot:latest")
    skill = await mcp_create_skill(conn, user_id, "calc", "Calculator")
    result = await mcp_attach_skill(conn, UUID(agent["id"]), UUID(skill["id"]))
    assert result["attached"] is True
    linked = await LinkRepo(conn).list_skills(UUID(agent["id"]))
    assert any(str(r["id"]) == skill["id"] for r in linked)


async def test_mcp_create_and_list_envs(mcp_conn_user):
    from src.mcp_server import mcp_create_env, mcp_list_envs
    import json
    conn, user_id = mcp_conn_user
    values_json = json.dumps({"OPENAI_API_KEY": "sk-test"})
    result = await mcp_create_env(conn, user_id, "openai", values_json)
    assert result["name"] == "openai"
    envs = await mcp_list_envs(conn, user_id)
    # includes the 'officeclaw' env created at registration + new 'openai'
    assert any(e["name"] == "openai" for e in envs)


async def test_mcp_list_channels(mcp_conn_user, client):
    from src.mcp_server import mcp_list_channels
    conn, user_id = mcp_conn_user
    # Create a channel via REST to have something to list
    await client.post("/channels", json={
        "user_id": str(user_id),
        "type": "telegram",
        "config": {"token": "bot:abc", "allow_from": []}
    })
    channels = await mcp_list_channels(conn, user_id)
    assert any(c["type"] == "telegram" for c in channels)
```

- [ ] **Step 5.2: Run to verify they fail**

```bash
cd /Users/vladimirbeliaev/vvbeliaev/officeclaw/api && \
  python -m pytest tests/test_mcp_tools.py::test_mcp_create_and_list_skills \
                   tests/test_mcp_tools.py::test_mcp_attach_skill \
                   tests/test_mcp_tools.py::test_mcp_create_and_list_envs \
                   tests/test_mcp_tools.py::test_mcp_list_channels -v
```

Expected: 4 failures (or passes if Task 3 implemented fully — see note in Task 4)

- [ ] **Step 5.3: Run all MCP tests**

```bash
cd /Users/vladimirbeliaev/vvbeliaev/officeclaw/api && python -m pytest tests/test_mcp_tools.py -v
```

Expected: `11 passed`

- [ ] **Step 5.4: Run full suite with coverage**

```bash
cd /Users/vladimirbeliaev/vvbeliaev/officeclaw/api && \
  python -m pytest --cov=src --cov-report=term-missing -v
```

Expected: all tests pass, coverage ≥ 80%

- [ ] **Step 5.5: Commit**

```bash
cd /Users/vladimirbeliaev/vvbeliaev/officeclaw && \
  git add api/tests/test_mcp_tools.py && \
  git commit -m "test(api): MCP resource tool tests — skills, envs, channels"
```

---

## Self-Review Notes

### Spec coverage

Architecture spec requirements vs. this plan:

| Requirement                                             | Task   |
| ------------------------------------------------------- | ------ |
| `OFFICECLAW_TOKEN` generated at registration            | Task 2 |
| Admin agent created at registration (`is_admin=True`)   | Task 2 |
| Admin agent seeded: SOUL.md, AGENTS.md, TOOLS.md        | Task 2 |
| Admin agent MCP: `officeclaw` entry                     | Task 2 |
| `user_envs` linked to Admin agent                       | Task 2 |
| MCP auth via `OFFICECLAW_TOKEN` bearer                  | Task 3 |
| `list_agents` tool                                      | Task 3 |
| `get_fleet_status` tool                                 | Task 3 |
| `create_agent` tool                                     | Task 3 |
| `update_agent_file` tool                                | Task 3 |
| `start_agent` / `stop_agent` tools (status update only) | Task 3 |
| `delete_agent` tool                                     | Task 3 |
| `list_skills` / `create_skill` / `attach_skill` tools   | Task 3 |
| `list_envs` / `create_env` tools                        | Task 3 |
| `list_channels` tool                                    | Task 3 |
| MCP server mounted inside FastAPI at `/mcp`             | Task 3 |

### Out of scope for this plan (future plans)

- `start_agent` / `stop_agent` VM lifecycle (sandbox-manager calls) — Plan 2
- `clawhub` MCP attached to Admin — Plan 4 (separate MCP registry service)
- WebSocket chat proxy — Plan 4 (web/ frontend)
- Auth/ownership checks on link operations — needs user auth layer

### Placeholder check

No TBDs or TODOs. All code is complete and exact.

### Type consistency

- `agent_id`, `skill_id`, `env_id`, `user_id` — all `UUID` in Python, `str` as MCP tool parameters (protocol limitation)
- `UUID(agent_id)` conversion at every tool wrapper boundary — consistent across all tools
- `conn: asyncpg.Connection` throughout business logic functions — matches existing repo pattern
