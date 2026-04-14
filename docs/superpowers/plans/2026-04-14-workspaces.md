# Workspaces Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce a `workspaces` table as the ownership unit for all fleet resources, allowing one user to have multiple self-contained fleet contexts.

**Architecture:** New `workspace` Python domain handles create/bootstrap/lookup. All app tables (`agents`, `skills`, `workspace_envs`, `workspace_channels`, `workspace_mcp`, `workspace_templates`) move from `user_id` → `workspace_id`. Web routing gains `/w/[workspaceId]/` prefix. MCP auth resolves token → workspace_id instead of user_id.

**Tech Stack:** PostgreSQL (asyncpg migrations), FastAPI (Python), SvelteKit + Drizzle ORM (TypeScript)

---

## File Map

**New Python files:**
- `api/src/workspace/__init__.py`
- `api/src/workspace/core/__init__.py`
- `api/src/workspace/core/schema.py`
- `api/src/workspace/core/ports/__init__.py`
- `api/src/workspace/core/ports/inbound.py`
- `api/src/workspace/core/ports/outbound.py`
- `api/src/workspace/app/__init__.py`
- `api/src/workspace/app/workspaces.py`
- `api/src/workspace/adapters/__init__.py`
- `api/src/workspace/adapters/_in/__init__.py`
- `api/src/workspace/adapters/_in/router.py`
- `api/src/workspace/adapters/out/__init__.py`
- `api/src/workspace/adapters/out/repository.py`
- `api/src/workspace/di.py`
- `api/tests/test_workspaces.py`

**Modified Python files:**
- `api/migrations/versions/001_initial_schema.sql` — full rewrite
- `api/src/fleet/core/schema.py` — `user_id` → `workspace_id`
- `api/src/fleet/core/ports/out.py` — `user_id` → `workspace_id`, `list_by_user` → `list_by_workspace`
- `api/src/fleet/adapters/out/repository.py` — SQL + `user_id` → `workspace_id`
- `api/src/fleet/app/agents.py` — method signatures
- `api/src/fleet/app/__init__.py` — `FleetApp` facade
- `api/src/fleet/adapters/_in/router.py` — request schemas
- `api/src/integrations/core/schema.py` — `user_id` → `workspace_id`
- `api/src/integrations/core/ports/outbound.py` — `user_id` → `workspace_id`
- `api/src/integrations/adapters/out/env_repo.py` — SQL: `user_envs` → `workspace_envs`, `user_id` → `workspace_id`
- `api/src/integrations/adapters/out/channel_repo.py` — SQL: `user_channels` → `workspace_channels`
- `api/src/integrations/adapters/out/mcp_repo.py` — SQL: `user_mcp` → `workspace_mcp`
- `api/src/integrations/adapters/out/template_repo.py` — SQL: `user_templates` → `workspace_templates`
- `api/src/integrations/app/env_service.py` — `user_id` → `workspace_id`
- `api/src/integrations/app/channel_service.py` — same
- `api/src/integrations/app/mcp_service.py` — same
- `api/src/integrations/app/template_service.py` — same
- `api/src/integrations/app/__init__.py` — `IntegrationsApp` facade
- `api/src/integrations/adapters/_in/router.py` — request schemas
- `api/src/library/core/schema.py` — `user_id` → `workspace_id`
- `api/src/library/core/ports/outbound.py` — same
- `api/src/library/adapters/out/repository.py` — SQL: `skills` table `user_id` → `workspace_id`
- `api/src/library/app/skills.py` — same
- `api/src/library/app/__init__.py` — facade
- `api/src/library/adapters/_in/router.py` — request schemas
- `api/src/identity/app/users.py` — remove `_bootstrap_admin`, delegate to `WorkspaceApp`
- `api/src/identity/app/__init__.py` — update `IdentityApp`
- `api/src/identity/adapters/out/repository.py` — remove `set_token`, `find_by_token`
- `api/src/identity/adapters/_in/router.py` — updated response schemas
- `api/src/identity/core/schema.py` — `UserRegistered` gets `workspace_id`
- `api/src/identity/di.py` — `build(pool, workspace)` instead of `build(pool, fleet, integrations)`
- `api/src/knowledge/adapters/_in/router.py` — `get_knowledge_user_id` → `get_knowledge_workspace_id`
- `api/src/knowledge/app/service.py` — `user_id` → `workspace_id`
- `api/src/knowledge/core/ports/_in.py` — `user_id` → `workspace_id`
- `api/src/entrypoint/mcp/__init__.py` — `_require_user` → `_require_workspace`, add `_workspace`
- `api/src/entrypoint/mcp/agents.py` — use `workspace_id`
- `api/src/entrypoint/mcp/envs.py` — same
- `api/src/entrypoint/mcp/channels.py` — same
- `api/src/entrypoint/mcp/mcp_servers.py` — same
- `api/src/entrypoint/mcp/skills.py` — same
- `api/src/entrypoint/mcp/templates.py` — same
- `api/src/entrypoint/mcp/knowledge.py` — same
- `api/src/entrypoint/main.py` — wire workspace domain, new wiring order
- `api/tests/conftest.py` — add `workspace_di`, update fixtures
- `api/tests/test_admin.py` — use `workspace_id` from response
- `api/tests/test_agents.py` — `user_id` fixture → `workspace_id`
- `api/tests/test_links.py` — same
- `api/tests/test_mcp_tools.py` — same

**New web files:**
- `web/src/routes/(app)/w/[workspaceId]/+layout.server.ts`
- `web/src/routes/(app)/w/[workspaceId]/+page.server.ts`
- `web/src/lib/components/workspace-switcher.svelte`

**Modified web files:**
- `web/src/lib/server/db/auth.schema.ts` — remove `officeclawToken` from user
- `web/src/lib/server/db/app.schema.ts` — add `workspaces`, rename tables, swap FKs
- `web/src/lib/server/auth.ts` — remove `officeclawToken` additionalField
- `web/src/routes/(app)/+layout.server.ts` — load workspaces list, remove workspace-specific queries
- `web/src/routes/(app)/+page.server.ts` — redirect to first workspace
- `web/src/routes/(app)/+layout.svelte` — add WorkspaceSwitcher
- `web/src/routes/api/agents/+server.ts` — send `workspace_id` instead of `user_id`

**Moved web directories** (routes under `(app)/` → `(app)/w/[workspaceId]/`):
- `agents/` → `w/[workspaceId]/agents/`
- `workspace/` → `w/[workspaceId]/workspace/`
- `prompts/` → `w/[workspaceId]/prompts/`

---

## Task 1: Rewrite SQL migration

**Files:**
- Rewrite: `api/migrations/versions/001_initial_schema.sql`

- [ ] **Step 1: Drop the old test database schema and repopulate**

  Before touching SQL: reset test DB so the new migration applies cleanly.

  ```bash
  psql postgresql://postgres:postgres@localhost:5434/officeclaw_test \
    -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
  ```

- [ ] **Step 2: Rewrite `api/migrations/versions/001_initial_schema.sql`**

  Replace the entire file with:

  ```sql
  -- ============================================================
  -- OfficeClaw — consolidated initial schema
  -- better-auth core tables + app domain tables
  -- ============================================================

  CREATE EXTENSION IF NOT EXISTS "pgcrypto";
  CREATE EXTENSION IF NOT EXISTS vector;

  -- ── better-auth ─────────────────────────────────────────────

  CREATE TABLE "user" (
      id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
      name             TEXT        NOT NULL DEFAULT '',
      email            TEXT        NOT NULL UNIQUE,
      email_verified   BOOLEAN     NOT NULL DEFAULT FALSE,
      image            TEXT,
      created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
      -- officeclaw_token removed: lives on workspaces now
  );

  CREATE TABLE "session" (
      id         TEXT        PRIMARY KEY,
      expires_at TIMESTAMPTZ NOT NULL,
      token      TEXT        NOT NULL UNIQUE,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      ip_address TEXT,
      user_agent TEXT,
      user_id    UUID        NOT NULL REFERENCES "user"(id) ON DELETE CASCADE
  );

  CREATE TABLE "account" (
      id                       TEXT        PRIMARY KEY,
      account_id               TEXT        NOT NULL,
      provider_id              TEXT        NOT NULL,
      user_id                  UUID        NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
      access_token             TEXT,
      refresh_token            TEXT,
      id_token                 TEXT,
      access_token_expires_at  TIMESTAMPTZ,
      refresh_token_expires_at TIMESTAMPTZ,
      scope                    TEXT,
      password                 TEXT,
      created_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      updated_at               TIMESTAMPTZ NOT NULL DEFAULT NOW()
  );

  CREATE TABLE "verification" (
      id         TEXT        PRIMARY KEY,
      identifier TEXT        NOT NULL,
      value      TEXT        NOT NULL,
      expires_at TIMESTAMPTZ NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
  );

  CREATE INDEX session_user_id_idx         ON "session"(user_id);
  CREATE INDEX account_user_id_idx         ON "account"(user_id);
  CREATE INDEX verification_identifier_idx ON "verification"(identifier);

  -- ── workspaces ──────────────────────────────────────────────

  CREATE TABLE workspaces (
      id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
      user_id          UUID        NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
      name             TEXT        NOT NULL,
      officeclaw_token TEXT        UNIQUE,
      created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
  );

  CREATE INDEX workspaces_user_id_idx ON workspaces(user_id);

  -- ── app domain ──────────────────────────────────────────────

  CREATE TYPE agent_status AS ENUM ('idle', 'running', 'error');

  CREATE TABLE agents (
      id           UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
      workspace_id UUID         NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
      name         TEXT         NOT NULL,
      status       agent_status NOT NULL DEFAULT 'idle',
      sandbox_id   TEXT,
      image        TEXT         NOT NULL DEFAULT 'localhost:5005/officeclaw/agent:latest',
      is_admin     BOOLEAN      NOT NULL DEFAULT FALSE,
      gateway_port INTEGER,
      avatar_url   TEXT,
      created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
      updated_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW()
  );

  CREATE TABLE agent_files (
      id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
      agent_id   UUID        NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
      path       TEXT        NOT NULL,
      content    TEXT        NOT NULL DEFAULT '',
      updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      UNIQUE(agent_id, path)
  );

  CREATE TABLE skills (
      id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
      workspace_id UUID       NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
      name        TEXT        NOT NULL,
      description TEXT        NOT NULL DEFAULT '',
      created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
  );

  CREATE TABLE skill_files (
      id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
      skill_id   UUID        NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
      path       TEXT        NOT NULL,
      content    TEXT        NOT NULL DEFAULT '',
      updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      UNIQUE(skill_id, path)
  );

  CREATE TABLE workspace_envs (
      id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
      workspace_id     UUID        NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
      name             TEXT        NOT NULL,
      values_encrypted BYTEA       NOT NULL,
      category         TEXT,
      created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      UNIQUE(workspace_id, name)
  );

  CREATE TABLE workspace_channels (
      id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
      workspace_id     UUID        NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
      name             TEXT        NOT NULL,
      type             TEXT        NOT NULL,
      config_encrypted BYTEA       NOT NULL,
      created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
  );

  CREATE TABLE workspace_mcp (
      id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
      workspace_id     UUID        NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
      name             TEXT        NOT NULL,
      type             TEXT        NOT NULL DEFAULT 'http',
      config_encrypted BYTEA       NOT NULL,
      created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      UNIQUE(workspace_id, name)
  );

  CREATE TABLE workspace_templates (
      id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
      workspace_id  UUID        NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
      name          TEXT        NOT NULL,
      template_type TEXT        NOT NULL CHECK (template_type IN ('user','soul','agents','heartbeat','tools')),
      content       TEXT        NOT NULL DEFAULT '',
      created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
      updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
  );

  CREATE TABLE agent_skills (
      agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
      skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
      PRIMARY KEY (agent_id, skill_id)
  );

  CREATE TABLE agent_envs (
      agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
      env_id   UUID NOT NULL REFERENCES workspace_envs(id) ON DELETE CASCADE,
      PRIMARY KEY (agent_id, env_id)
  );

  CREATE TABLE agent_channels (
      agent_id   UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
      channel_id UUID NOT NULL REFERENCES workspace_channels(id) ON DELETE CASCADE,
      PRIMARY KEY (agent_id, channel_id),
      UNIQUE(channel_id)
  );

  CREATE TABLE agent_mcp (
      agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
      mcp_id   UUID NOT NULL REFERENCES workspace_mcp(id) ON DELETE CASCADE,
      PRIMARY KEY (agent_id, mcp_id)
  );

  CREATE TABLE agent_user_templates (
      agent_id          UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
      user_template_id  UUID NOT NULL REFERENCES workspace_templates(id) ON DELETE CASCADE,
      template_type     TEXT NOT NULL CHECK (template_type IN ('user','soul','agents','heartbeat','tools')),
      PRIMARY KEY (agent_id, user_template_id),
      UNIQUE (agent_id, template_type)
  );
  ```

- [ ] **Step 3: Commit**

  ```bash
  git add api/migrations/versions/001_initial_schema.sql
  git commit -m "feat(schema): introduce workspaces table, rename user_* tables to workspace_*"
  ```

---

## Task 2: workspace domain — core (schema + ports)

**Files:**
- Create: `api/src/workspace/__init__.py`
- Create: `api/src/workspace/core/__init__.py`
- Create: `api/src/workspace/core/schema.py`
- Create: `api/src/workspace/core/ports/__init__.py`
- Create: `api/src/workspace/core/ports/inbound.py`
- Create: `api/src/workspace/core/ports/outbound.py`

- [ ] **Step 1: Write the failing test for WorkspaceRepo**

  Create `api/tests/test_workspaces.py`:

  ```python
  # api/tests/test_workspaces.py
  from uuid import UUID
  import pytest


  @pytest.fixture
  async def workspace_deps(conn):
      import src.workspace.di as workspace_di
      return workspace_di.build(conn, None, None)  # type: ignore — repo only for unit tests


  async def test_create_workspace_returns_record(client):
      user_resp = await client.post("/users", json={"email": "ws-create@example.com"})
      assert user_resp.status_code == 201
      body = user_resp.json()
      assert "workspace_id" in body
      assert "officeclaw_token" in body
      assert len(body["officeclaw_token"]) > 20


  async def test_list_workspaces(client):
      user_resp = await client.post("/users", json={"email": "ws-list@example.com"})
      user_id = user_resp.json()["id"]
      resp = await client.get(f"/workspaces?user_id={user_id}")
      assert resp.status_code == 200
      workspaces = resp.json()
      assert len(workspaces) == 1
      assert workspaces[0]["name"] == "Personal"


  async def test_create_second_workspace(client):
      user_resp = await client.post("/users", json={"email": "ws-second@example.com"})
      user_id = user_resp.json()["id"]
      resp = await client.post("/workspaces", json={"user_id": user_id, "name": "Work"})
      assert resp.status_code == 201
      body = resp.json()
      assert body["name"] == "Work"
      assert "officeclaw_token" in body
      assert "id" in body


  async def test_second_workspace_has_admin_agent(client, fleet_deps):
      user_resp = await client.post("/users", json={"email": "ws-admin@example.com"})
      user_id = user_resp.json()["id"]
      ws_resp = await client.post("/workspaces", json={"user_id": user_id, "name": "Work"})
      workspace_id = UUID(ws_resp.json()["id"])
      agents = await fleet_deps.list_agents(workspace_id)
      admin = [a for a in agents if a["is_admin"]]
      assert len(admin) == 1
  ```

- [ ] **Step 2: Run test — expect import failure**

  ```bash
  cd api && python -m pytest tests/test_workspaces.py -v 2>&1 | head -20
  ```

  Expected: `ModuleNotFoundError: No module named 'src.workspace'`

- [ ] **Step 3: Create workspace domain skeleton**

  ```bash
  mkdir -p api/src/workspace/core/ports
  mkdir -p api/src/workspace/app
  mkdir -p api/src/workspace/adapters/_in
  mkdir -p api/src/workspace/adapters/out
  touch api/src/workspace/__init__.py
  touch api/src/workspace/core/__init__.py
  touch api/src/workspace/core/ports/__init__.py
  touch api/src/workspace/app/__init__.py
  touch api/src/workspace/adapters/__init__.py
  touch api/src/workspace/adapters/_in/__init__.py
  touch api/src/workspace/adapters/out/__init__.py
  ```

- [ ] **Step 4: Write `api/src/workspace/core/schema.py`**

  ```python
  from datetime import datetime
  from uuid import UUID
  from pydantic import BaseModel


  class WorkspaceCreate(BaseModel):
      user_id: UUID
      name: str


  class WorkspaceOut(BaseModel):
      id: UUID
      user_id: UUID
      name: str
      officeclaw_token: str
      created_at: datetime
  ```

- [ ] **Step 5: Write `api/src/workspace/core/ports/outbound.py`**

  ```python
  from typing import Protocol
  from uuid import UUID


  class IWorkspaceRepo(Protocol):
      async def create(self, user_id: UUID, name: str, token: str) -> dict: ...
      async def find_by_id(self, workspace_id: UUID) -> dict | None: ...
      async def find_by_token(self, token: str) -> dict | None: ...
      async def list_by_user(self, user_id: UUID) -> list[dict]: ...
  ```

- [ ] **Step 6: Write `api/src/workspace/core/ports/inbound.py`**

  ```python
  from typing import Protocol
  from uuid import UUID


  class IWorkspaceApp(Protocol):
      async def create_workspace(self, user_id: UUID, name: str) -> dict: ...
      async def list_workspaces(self, user_id: UUID) -> list[dict]: ...
      async def find_by_token(self, token: str) -> dict | None: ...
  ```

- [ ] **Step 7: Commit skeleton**

  ```bash
  git add api/src/workspace/ api/tests/test_workspaces.py
  git commit -m "feat(workspace): add workspace domain skeleton and failing tests"
  ```

---

## Task 3: workspace domain — repository

**Files:**
- Create: `api/src/workspace/adapters/out/repository.py`

- [ ] **Step 1: Write `api/src/workspace/adapters/out/repository.py`**

  ```python
  from uuid import UUID

  import asyncpg


  class WorkspaceRepo:
      def __init__(self, conn: asyncpg.Pool) -> None:
          self._conn = conn

      async def create(self, user_id: UUID, name: str, token: str) -> asyncpg.Record:
          return await self._conn.fetchrow(
              "INSERT INTO workspaces (user_id, name, officeclaw_token)"
              " VALUES ($1, $2, $3) RETURNING *",
              user_id, name, token,
          )

      async def find_by_id(self, workspace_id: UUID) -> asyncpg.Record | None:
          return await self._conn.fetchrow(
              "SELECT * FROM workspaces WHERE id = $1", workspace_id
          )

      async def find_by_token(self, token: str) -> asyncpg.Record | None:
          return await self._conn.fetchrow(
              "SELECT * FROM workspaces WHERE officeclaw_token = $1", token
          )

      async def list_by_user(self, user_id: UUID) -> list[asyncpg.Record]:
          return await self._conn.fetch(
              "SELECT * FROM workspaces WHERE user_id = $1 ORDER BY created_at ASC",
              user_id,
          )
  ```

---

## Task 4: workspace domain — service + app facade

**Files:**
- Create: `api/src/workspace/app/workspaces.py`
- Modify: `api/src/workspace/app/__init__.py`

- [ ] **Step 1: Write `api/src/workspace/app/workspaces.py`**

  This is the bootstrap logic moved from `UserService._bootstrap_admin`. It takes `workspace_id` instead of `user_id`.

  ```python
  """WorkspaceService — creates workspaces and runs per-workspace bootstrap."""
  from __future__ import annotations

  import secrets
  from typing import TYPE_CHECKING
  from uuid import UUID

  import asyncpg

  from src.workspace.adapters.out.repository import WorkspaceRepo
  from src.shared.config import get_settings

  if TYPE_CHECKING:
      from src.fleet.app import FleetApp
      from src.integrations.app import IntegrationsApp

  _SOUL_MD = """
  You are the Admin agent for OfficeClaw -- a fleet manager AI that helps users
  create, configure, and manage their personal AI agents.

  You have access to the `officeclaw` MCP tool which allows you to perform all
  fleet operations: creating agents, installing skills, configuring channels,
  managing environment variables, and monitoring fleet status.

  When the user asks you to do something with their agents, use the officeclaw
  tools to make it happen. Be proactive and helpful. When creating agents,
  suggest good names and configurations. When installing skills, explain what
  the skill does.

  Always confirm important actions (deleting agents, changing configurations)
  before executing them.
  """

  _AGENTS_MD = """
  # Agents

  You operate as a fleet manager. Your job is to help the user build and manage
  their fleet of AI agents.

  ## Available MCP Tools
  - officeclaw: Fleet management (create/start/stop/delete agents, manage skills, envs, channels)
  """

  _TOOLS_MD = """
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


  class WorkspaceService:
      def __init__(
          self,
          repo: WorkspaceRepo,
          fleet: FleetApp,
          integrations: IntegrationsApp,
      ) -> None:
          self._repo = repo
          self._fleet = fleet
          self._integrations = integrations

      async def create_workspace(self, user_id: UUID, name: str) -> asyncpg.Record:
          """Create workspace + run full bootstrap. Returns workspace record with token."""
          token = secrets.token_urlsafe(32)
          workspace = await self._repo.create(user_id, name, token)
          workspace_id = workspace["id"]
          await self._bootstrap(workspace_id, token)
          return workspace

      async def list_workspaces(self, user_id: UUID) -> list[asyncpg.Record]:
          return await self._repo.list_by_user(user_id)

      async def find_by_token(self, token: str) -> asyncpg.Record | None:
          return await self._repo.find_by_token(token)

      async def _bootstrap(self, workspace_id: UUID, token: str) -> None:
          """Create Admin agent and all seed resources for a new workspace."""
          settings = get_settings()

          env_record = await self._integrations.create_env(
              workspace_id, "officeclaw", {"OFFICECLAW_TOKEN": token}, category="system"
          )

          default_llm_env = await self._integrations.create_env(
              workspace_id,
              "default-llm",
              {
                  "OFFICECLAW_LLM_API_KEY": settings.default_llm_api_key,
                  "OFFICECLAW_LLM_BASE_URL": settings.default_llm_base_url,
                  "OFFICECLAW_LLM_MODEL": settings.default_llm_model,
              },
              category="llm-provider",
          )

          agent_record = await self._fleet.create_agent(
              workspace_id, "Admin", "localhost:5005/officeclaw/agent:latest", is_admin=True
          )
          agent_id = agent_record["id"]

          await self._fleet.upsert_file(agent_id, "SOUL.md", _SOUL_MD)
          await self._fleet.upsert_file(agent_id, "AGENTS.md", _AGENTS_MD)
          await self._fleet.upsert_file(agent_id, "TOOLS.md", _TOOLS_MD)

          mcp_url = f"{settings.mcp_base_url}/mcp/admin"
          mcp_record = await self._integrations.create_mcp(
              workspace_id,
              "officeclaw-admin",
              "http",
              {
                  "url": mcp_url,
                  "headers": {"Authorization": "Bearer ${OFFICECLAW_TOKEN}"},
              },
          )

          await self._integrations.attach_mcp(agent_id, mcp_record["id"])
          await self._integrations.attach_env(agent_id, env_record["id"])
          await self._integrations.attach_env(agent_id, default_llm_env["id"])
  ```

- [ ] **Step 2: Write `api/src/workspace/app/__init__.py`**

  ```python
  from uuid import UUID

  import asyncpg

  from src.workspace.app.workspaces import WorkspaceService


  class WorkspaceApp:
      def __init__(self, service: WorkspaceService) -> None:
          self._service = service

      async def create_workspace(self, user_id: UUID, name: str) -> asyncpg.Record:
          return await self._service.create_workspace(user_id, name)

      async def list_workspaces(self, user_id: UUID) -> list[asyncpg.Record]:
          return await self._service.list_workspaces(user_id)

      async def find_by_token(self, token: str) -> asyncpg.Record | None:
          return await self._service.find_by_token(token)
  ```

---

## Task 5: workspace domain — router + DI + wire into main.py

**Files:**
- Create: `api/src/workspace/adapters/_in/router.py`
- Create: `api/src/workspace/di.py`
- Modify: `api/src/entrypoint/main.py`

- [ ] **Step 1: Write `api/src/workspace/adapters/_in/router.py`**

  ```python
  from uuid import UUID

  from fastapi import APIRouter, Depends, HTTPException, Request

  from src.workspace.app import WorkspaceApp
  from src.workspace.core.schema import WorkspaceCreate, WorkspaceOut

  router = APIRouter()


  def get_workspace(request: Request) -> WorkspaceApp:
      return request.app.state.workspace


  @router.post("", response_model=WorkspaceOut, status_code=201)
  async def create_workspace(
      body: WorkspaceCreate,
      workspace: WorkspaceApp = Depends(get_workspace),
  ) -> WorkspaceOut:
      record = await workspace.create_workspace(body.user_id, body.name)
      return WorkspaceOut(**dict(record))


  @router.get("", response_model=list[WorkspaceOut])
  async def list_workspaces(
      user_id: UUID,
      workspace: WorkspaceApp = Depends(get_workspace),
  ) -> list[WorkspaceOut]:
      records = await workspace.list_workspaces(user_id)
      return [WorkspaceOut(**dict(r)) for r in records]
  ```

- [ ] **Step 2: Write `api/src/workspace/di.py`**

  ```python
  from __future__ import annotations

  from typing import TYPE_CHECKING

  import asyncpg

  from src.workspace.adapters.out.repository import WorkspaceRepo
  from src.workspace.app import WorkspaceApp
  from src.workspace.app.workspaces import WorkspaceService

  if TYPE_CHECKING:
      from src.fleet.app import FleetApp
      from src.integrations.app import IntegrationsApp


  def build(
      pool: asyncpg.Pool,
      fleet: FleetApp,
      integrations: IntegrationsApp,
  ) -> WorkspaceApp:
      repo = WorkspaceRepo(pool)
      service = WorkspaceService(repo, fleet, integrations)
      return WorkspaceApp(service)
  ```

- [ ] **Step 3: Update `api/src/entrypoint/main.py`**

  Add workspace import and wire it into lifespan + router. Replace the file:

  ```python
  from collections.abc import AsyncGenerator
  from contextlib import asynccontextmanager
  from pathlib import Path

  import asyncpg
  from fastapi import FastAPI
  from fastapi.staticfiles import StaticFiles

  from src.shared.config import get_settings
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

      integrations = integrations_di.build(pool)
      library = library_di.build(pool)
      fleet, watcher = fleet_di.build(pool, integrations, library)
      workspace = workspace_di.build(pool, fleet, integrations)
      identity = identity_di.build(pool, workspace)
      knowledge = knowledge_di.build(settings)

      app.state.pool = pool
      app.state.fleet = fleet
      app.state.identity = identity
      app.state.library = library
      app.state.integrations = integrations
      app.state.workspace = workspace
      app.state.knowledge = knowledge

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

      uploads_dir = Path("uploads")
      uploads_dir.mkdir(exist_ok=True)
      app.mount("/static", StaticFiles(directory=uploads_dir), name="static")
      app.mount("/mcp/admin", _admin_mcp_asgi)
      app.mount("/mcp/knowledge", _knowledge_mcp_asgi)

      return app


  app = create_app()
  ```

- [ ] **Step 4: Commit**

  ```bash
  git add api/src/workspace/ api/src/entrypoint/main.py
  git commit -m "feat(workspace): add workspace router, DI, wire into main"
  ```

---

## Task 6: Update fleet domain — `user_id` → `workspace_id`

**Files:**
- Modify: `api/src/fleet/core/schema.py`
- Modify: `api/src/fleet/core/ports/out.py`
- Modify: `api/src/fleet/adapters/out/repository.py`
- Modify: `api/src/fleet/app/agents.py`
- Modify: `api/src/fleet/app/__init__.py`
- Modify: `api/src/fleet/adapters/_in/router.py`

- [ ] **Step 1: Update `api/src/fleet/core/schema.py`**

  Replace `user_id` with `workspace_id` in `AgentCreate` and `AgentOut`:

  ```python
  from datetime import datetime
  from uuid import UUID
  from typing import Literal
  from pydantic import BaseModel

  AgentStatus = Literal["idle", "running", "error"]


  class AgentCreate(BaseModel):
      workspace_id: UUID
      name: str
      image: str = "localhost:5005/officeclaw/agent:latest"
      is_admin: bool = False


  class AgentUpdate(BaseModel):
      name: str | None = None
      status: AgentStatus | None = None
      sandbox_id: str | None = None
      avatar_url: str | None = None


  class AgentOut(BaseModel):
      id: UUID
      workspace_id: UUID
      name: str
      status: str
      sandbox_id: str | None
      gateway_port: int | None
      image: str
      is_admin: bool
      avatar_url: str | None
      created_at: datetime
      updated_at: datetime


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

- [ ] **Step 2: Update `api/src/fleet/core/ports/out.py`**

  ```python
  from typing import Protocol
  from uuid import UUID


  class IAgentRepo(Protocol):
      async def create(
          self, workspace_id: UUID, name: str, image: str, is_admin: bool
      ) -> dict: ...
      async def find_by_id(self, agent_id: UUID) -> dict | None: ...
      async def list_by_workspace(self, workspace_id: UUID) -> list[dict]: ...
      async def list_running(self) -> list[dict]: ...
      async def update(self, agent_id: UUID, **kwargs) -> dict | None: ...
      async def delete(self, agent_id: UUID) -> None: ...


  class IAgentFileRepo(Protocol):
      async def upsert(self, agent_id: UUID, path: str, content: str) -> dict: ...
      async def find(self, agent_id: UUID, path: str) -> dict | None: ...
      async def list_by_agent(self, agent_id: UUID) -> list[dict]: ...
      async def bulk_upsert(self, agent_id: UUID, files: list[dict]) -> None: ...
  ```

- [ ] **Step 3: Update `api/src/fleet/adapters/out/repository.py`**

  Replace `user_id` with `workspace_id` and update SQL table column + method names:

  ```python
  from uuid import UUID
  import asyncpg

  _ALLOWED_UPDATE_FIELDS = frozenset(
      {"name", "status", "sandbox_id", "gateway_port", "avatar_url"}
  )


  class AgentRepo:
      def __init__(self, conn: asyncpg.Pool) -> None:
          self._conn = conn

      async def create(
          self, workspace_id: UUID, name: str, image: str, is_admin: bool
      ) -> asyncpg.Record:
          return await self._conn.fetchrow(
              "INSERT INTO agents (workspace_id, name, image, is_admin)"
              " VALUES ($1, $2, $3, $4) RETURNING *",
              workspace_id, name, image, is_admin,
          )

      async def find_by_id(self, agent_id: UUID) -> asyncpg.Record | None:
          return await self._conn.fetchrow(
              "SELECT * FROM agents WHERE id = $1", agent_id
          )

      async def list_by_workspace(self, workspace_id: UUID) -> list[asyncpg.Record]:
          return await self._conn.fetch(
              "SELECT * FROM agents WHERE workspace_id = $1", workspace_id
          )

      async def list_running(self) -> list[asyncpg.Record]:
          return await self._conn.fetch(
              "SELECT * FROM agents WHERE status = 'running'"
          )

      async def update(self, agent_id: UUID, **fields) -> asyncpg.Record | None:
          unknown = set(fields) - _ALLOWED_UPDATE_FIELDS
          if unknown:
              raise ValueError(f"Unknown agent fields: {unknown}")
          set_clauses = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(fields))
          values = list(fields.values())
          return await self._conn.fetchrow(
              f"UPDATE agents SET {set_clauses}, updated_at = NOW() WHERE id = $1 RETURNING *",
              agent_id, *values,
          )

      async def delete(self, agent_id: UUID) -> None:
          await self._conn.execute("DELETE FROM agents WHERE id = $1", agent_id)
  ```

  Keep `AgentFileRepo` unchanged (it only uses `agent_id`).

- [ ] **Step 4: Update `api/src/fleet/app/agents.py`**

  ```python
  from uuid import UUID

  from src.fleet.core.ports.out import IAgentRepo, IAgentFileRepo


  class AgentService:
      def __init__(self, agent_repo: IAgentRepo, file_repo: IAgentFileRepo) -> None:
          self._agents = agent_repo
          self._files = file_repo

      async def create(
          self, workspace_id: UUID, name: str, image: str, is_admin: bool = False
      ) -> dict:
          return await self._agents.create(workspace_id, name, image, is_admin)

      async def find_by_id(self, agent_id: UUID) -> dict | None:
          return await self._agents.find_by_id(agent_id)

      async def list_by_workspace(self, workspace_id: UUID) -> list[dict]:
          return await self._agents.list_by_workspace(workspace_id)

      async def list_running(self) -> list[dict]:
          return await self._agents.list_running()

      async def update(self, agent_id: UUID, **fields: object) -> dict | None:
          return await self._agents.update(agent_id, **fields)

      async def delete(self, agent_id: UUID) -> None:
          await self._agents.delete(agent_id)

      async def upsert_file(self, agent_id: UUID, path: str, content: str) -> dict:
          return await self._files.upsert(agent_id, path, content)

      async def find_file(self, agent_id: UUID, path: str) -> dict | None:
          return await self._files.find(agent_id, path)

      async def list_files(self, agent_id: UUID) -> list[dict]:
          return await self._files.list_by_agent(agent_id)

      async def bulk_upsert_files(self, agent_id: UUID, files: list[dict]) -> None:
          await self._files.bulk_upsert(agent_id, files)
  ```

- [ ] **Step 5: Update `api/src/fleet/app/__init__.py`**

  Replace `user_id` → `workspace_id` and `list_by_user` → `list_by_workspace` throughout. The auto-attach LLM env on create also uses `workspace_id`:

  ```python
  from __future__ import annotations

  from typing import TYPE_CHECKING
  from uuid import UUID

  import asyncpg

  from src.fleet.app.agents import AgentService
  from src.fleet.app.sandbox import SandboxService

  if TYPE_CHECKING:
      from src.integrations.app import IntegrationsApp


  class FleetApp:
      def __init__(
          self,
          agents: AgentService,
          sandbox: SandboxService,
          integrations: IntegrationsApp,
      ) -> None:
          self._agents = agents
          self._sandbox = sandbox
          self._integrations = integrations

      async def create_agent(
          self, workspace_id: UUID, name: str, image: str, is_admin: bool = False
      ) -> asyncpg.Record:
          record = await self._agents.create(workspace_id, name, image, is_admin)
          if not is_admin:
              llm_env = await self._integrations.find_llm_provider(workspace_id)
              if llm_env:
                  await self._integrations.attach_env(record["id"], llm_env["id"])
          return record

      async def find_agent(self, agent_id: UUID) -> asyncpg.Record | None:
          return await self._agents.find_by_id(agent_id)

      async def list_agents(self, workspace_id: UUID) -> list[asyncpg.Record]:
          return await self._agents.list_by_workspace(workspace_id)

      async def update_agent(self, agent_id: UUID, **fields: object) -> asyncpg.Record | None:
          return await self._agents.update(agent_id, **fields)

      async def delete_agent(self, agent_id: UUID) -> None:
          await self._agents.delete(agent_id)

      async def upsert_file(self, agent_id: UUID, path: str, content: str) -> asyncpg.Record:
          return await self._agents.upsert_file(agent_id, path, content)

      async def find_file(self, agent_id: UUID, path: str) -> asyncpg.Record | None:
          return await self._agents.find_file(agent_id, path)

      async def list_files(self, agent_id: UUID) -> list[asyncpg.Record]:
          return await self._agents.list_files(agent_id)

      async def start_sandbox(self, agent_id: UUID) -> str:
          return await self._sandbox.start(agent_id)

      async def stop_sandbox(self, agent_id: UUID) -> None:
          await self._sandbox.stop(agent_id)
  ```

- [ ] **Step 6: Update `api/src/fleet/adapters/_in/router.py`**

  Change `body.user_id` → `body.workspace_id` in `create_agent` handler. Only the POST handler changes:

  ```python
  @router.post("", response_model=AgentOut, status_code=201)
  async def create_agent(
      body: AgentCreate,
      fleet: FleetApp = Depends(get_fleet),
  ) -> AgentOut:
      record = await fleet.create_agent(
          body.workspace_id, body.name, body.image, body.is_admin
      )
      return AgentOut(**dict(record))
  ```

  The `GET /{agent_id}`, `PATCH`, `DELETE`, file routes are unchanged.

- [ ] **Step 7: Commit**

  ```bash
  git add api/src/fleet/
  git commit -m "feat(fleet): replace user_id with workspace_id throughout fleet domain"
  ```

---

## Task 7: Update integrations domain — `user_id` → `workspace_id`

**Files:**
- Modify: `api/src/integrations/core/schema.py`
- Modify: `api/src/integrations/core/ports/outbound.py`
- Modify: `api/src/integrations/adapters/out/env_repo.py`
- Modify: `api/src/integrations/adapters/out/channel_repo.py`
- Modify: `api/src/integrations/adapters/out/mcp_repo.py`
- Modify: `api/src/integrations/adapters/out/template_repo.py`
- Modify: `api/src/integrations/app/env_service.py`
- Modify: `api/src/integrations/app/channel_service.py`
- Modify: `api/src/integrations/app/mcp_service.py`
- Modify: `api/src/integrations/app/template_service.py`
- Modify: `api/src/integrations/app/__init__.py`
- Modify: `api/src/integrations/adapters/_in/router.py`

- [ ] **Step 1: Update `api/src/integrations/core/schema.py`**

  Replace every `user_id: UUID` field with `workspace_id: UUID` in all Create/Out schemas. Also replace `user_id` field name in Out models:

  In `EnvCreate`: `user_id` → `workspace_id`. In `EnvOut`: `user_id` → `workspace_id`.
  Same pattern for `ChannelCreate`/`ChannelOut`, `McpCreate`/`McpOut`, `TemplateCreate`/`TemplateOut`.

  Read the current file first, then apply find-and-replace: `user_id` → `workspace_id` everywhere in this file.

- [ ] **Step 2: Update `api/src/integrations/core/ports/outbound.py`**

  Replace all `user_id: UUID` params with `workspace_id: UUID`. Replace all `list_by_user` method names with `list_by_workspace`. Example:

  ```python
  class IEnvRepo(Protocol):
      async def create(self, workspace_id: UUID, name: str, values: dict, category: str | None = None) -> asyncpg.Record: ...
      async def find_by_id(self, env_id: UUID) -> asyncpg.Record | None: ...
      async def list_by_workspace(self, workspace_id: UUID) -> list[asyncpg.Record]: ...
      async def find_llm_provider_by_workspace(self, workspace_id: UUID) -> asyncpg.Record | None: ...
      async def get_decrypted_values(self, env_id: UUID) -> dict: ...
      async def update(self, env_id: UUID, name: str | None = None, values: dict | None = None, category: str | None = None) -> asyncpg.Record | None: ...
      async def delete(self, env_id: UUID) -> None: ...

  class IChannelRepo(Protocol):
      async def create(self, workspace_id: UUID, name: str, type_: str, config: dict) -> asyncpg.Record: ...
      async def find_by_id(self, channel_id: UUID) -> asyncpg.Record | None: ...
      async def list_by_workspace(self, workspace_id: UUID) -> list[asyncpg.Record]: ...
      async def get_decrypted_config(self, channel_id: UUID) -> dict: ...
      async def delete(self, channel_id: UUID) -> None: ...

  class IUserMcpRepo(Protocol):
      async def create(self, workspace_id: UUID, name: str, type_: str, config: dict) -> asyncpg.Record: ...
      async def find_by_id(self, mcp_id: UUID) -> asyncpg.Record | None: ...
      async def list_by_workspace(self, workspace_id: UUID) -> list[asyncpg.Record]: ...
      async def get_decrypted_config(self, mcp_id: UUID) -> dict: ...
      async def delete(self, mcp_id: UUID) -> None: ...

  class IUserTemplateRepo(Protocol):
      async def create(self, workspace_id: UUID, name: str, template_type: str, content: str) -> asyncpg.Record: ...
      async def find_by_id(self, template_id: UUID) -> asyncpg.Record | None: ...
      async def list_by_workspace(self, workspace_id: UUID) -> list[asyncpg.Record]: ...
      async def update(self, template_id: UUID, name: str | None = None, content: str | None = None) -> asyncpg.Record | None: ...
      async def delete(self, template_id: UUID) -> None: ...
  ```

- [ ] **Step 3: Update all four repo files**

  In each repo, apply these changes:
  - Method param `user_id` → `workspace_id`
  - SQL column `user_id` → `workspace_id`
  - Table names: `user_envs` → `workspace_envs`, `user_channels` → `workspace_channels`, `user_mcp` → `workspace_mcp`, `user_templates` → `workspace_templates`
  - Method name `list_by_user` → `list_by_workspace`
  - Method name `find_llm_provider_by_user` → `find_llm_provider_by_workspace`

  **`env_repo.py`** — example of one method after change:
  ```python
  async def create(self, workspace_id: UUID, name: str, values: dict, category: str | None = None) -> asyncpg.Record:
      encrypted = encrypt_json(values)
      return await self._conn.fetchrow(
          "INSERT INTO workspace_envs (workspace_id, name, values_encrypted, category)"
          " VALUES ($1, $2, $3, $4)"
          " RETURNING id, workspace_id, name, category, created_at",
          workspace_id, name, encrypted, category,
      )

  async def list_by_workspace(self, workspace_id: UUID) -> list[asyncpg.Record]:
      return await self._conn.fetch(
          "SELECT id, workspace_id, name, category, created_at FROM workspace_envs WHERE workspace_id = $1",
          workspace_id,
      )

  async def find_llm_provider_by_workspace(self, workspace_id: UUID) -> asyncpg.Record | None:
      return await self._conn.fetchrow(
          "SELECT id, workspace_id, name, category, created_at FROM workspace_envs"
          " WHERE workspace_id = $1 AND category = 'llm-provider'"
          " ORDER BY (name = 'default-llm') DESC, created_at ASC"
          " LIMIT 1",
          workspace_id,
      )
  ```

  Apply the same pattern to `channel_repo.py`, `mcp_repo.py`, `template_repo.py`.

- [ ] **Step 4: Update four service files**

  In `env_service.py`, `channel_service.py`, `mcp_service.py`, `template_service.py`:
  - Method param `user_id` → `workspace_id`
  - Delegate calls: `list_by_user` → `list_by_workspace`, `find_llm_provider_by_user` → `find_llm_provider_by_workspace`

  Example for `env_service.py`:
  ```python
  async def create(self, workspace_id: UUID, name: str, values: dict, category: str | None = None) -> asyncpg.Record:
      return await self._repo.create(workspace_id, name, values, category)

  async def list(self, workspace_id: UUID) -> list[asyncpg.Record]:
      return await self._repo.list_by_workspace(workspace_id)

  async def find_llm_provider(self, workspace_id: UUID) -> asyncpg.Record | None:
      return await self._repo.find_llm_provider_by_workspace(workspace_id)
  ```

- [ ] **Step 5: Update `api/src/integrations/app/__init__.py`**

  Replace all `user_id` params and method calls in `IntegrationsApp`. The pattern is consistent: every method that previously accepted `user_id` now accepts `workspace_id`, and calls the renamed service methods. Example:

  ```python
  async def create_env(self, workspace_id: UUID, name: str, values: dict, category: str | None = None) -> asyncpg.Record:
      return await self._envs.create(workspace_id, name, values, category)

  async def list_envs(self, workspace_id: UUID) -> list[asyncpg.Record]:
      return await self._envs.list(workspace_id)

  async def find_llm_provider(self, workspace_id: UUID) -> asyncpg.Record | None:
      return await self._envs.find_llm_provider(workspace_id)

  async def create_channel(self, workspace_id: UUID, name: str, type_: str, config: dict) -> asyncpg.Record:
      return await self._channels.create(workspace_id, name, type_, config)

  async def list_channels(self, workspace_id: UUID) -> list[asyncpg.Record]:
      return await self._channels.list(workspace_id)

  async def create_mcp(self, workspace_id: UUID, name: str, type_: str, config: dict) -> asyncpg.Record:
      return await self._mcp.create(workspace_id, name, type_, config)

  async def list_mcps(self, workspace_id: UUID) -> list[asyncpg.Record]:
      return await self._mcp.list(workspace_id)

  async def create_template(self, workspace_id: UUID, name: str, template_type: str, content: str) -> asyncpg.Record:
      return await self._templates.create(workspace_id, name, template_type, content)

  async def list_templates(self, workspace_id: UUID) -> list[asyncpg.Record]:
      return await self._templates.list(workspace_id)
  ```

- [ ] **Step 6: Update `api/src/integrations/adapters/_in/router.py`**

  In each router handler, replace `body.user_id` → `body.workspace_id`. The `user_id` query param in GET list endpoints → `workspace_id`. Example:

  ```python
  @envs_router.post("", response_model=EnvOut, status_code=201)
  async def create_env(body: EnvCreate, deps: IntegrationsApp = Depends(get_integrations)) -> EnvOut:
      try:
          record = await deps.create_env(body.workspace_id, body.name, body.values, body.category)
      except asyncpg.UniqueViolationError:
          raise HTTPException(409, "Env name already exists for this workspace")
      return EnvOut(**dict(record))
  ```

- [ ] **Step 7: Commit**

  ```bash
  git add api/src/integrations/
  git commit -m "feat(integrations): replace user_id with workspace_id, rename user_* tables"
  ```

---

## Task 8: Update library domain — `user_id` → `workspace_id`

**Files:**
- Modify: `api/src/library/core/schema.py`
- Modify: `api/src/library/core/ports/outbound.py`
- Modify: `api/src/library/adapters/out/repository.py`
- Modify: `api/src/library/app/skills.py`
- Modify: `api/src/library/app/__init__.py`
- Modify: `api/src/library/adapters/_in/router.py`

- [ ] **Step 1: Apply `user_id` → `workspace_id` across library domain**

  Same pattern as Task 7. In `SkillCreate`/`SkillOut`: `user_id` → `workspace_id`. In repo SQL: `WHERE user_id = $1` → `WHERE workspace_id = $1`. Method `list_by_user` → `list_by_workspace`. Skills table already keeps the name `skills` — only the FK column changes.

  In `repository.py`:
  ```python
  async def create(self, workspace_id: UUID, name: str, description: str) -> asyncpg.Record:
      return await self._conn.fetchrow(
          "INSERT INTO skills (workspace_id, name, description) VALUES ($1, $2, $3) RETURNING *",
          workspace_id, name, description,
      )

  async def list_by_workspace(self, workspace_id: UUID) -> list[asyncpg.Record]:
      return await self._conn.fetch(
          "SELECT * FROM skills WHERE workspace_id = $1", workspace_id
      )
  ```

- [ ] **Step 2: Commit**

  ```bash
  git add api/src/library/
  git commit -m "feat(library): replace user_id with workspace_id in skills domain"
  ```

---

## Task 9: Update identity domain — delegate bootstrap to workspace

**Files:**
- Modify: `api/src/identity/app/users.py`
- Modify: `api/src/identity/app/__init__.py`
- Modify: `api/src/identity/adapters/out/repository.py`
- Modify: `api/src/identity/adapters/_in/router.py`
- Modify: `api/src/identity/core/schema.py`
- Modify: `api/src/identity/di.py`

- [ ] **Step 1: Update `api/src/identity/core/schema.py`**

  `UserRegistered` now includes `workspace_id`. `BootstrapOut` also gets `workspace_id`:

  ```python
  from datetime import datetime
  from uuid import UUID
  from pydantic import BaseModel


  class UserCreate(BaseModel):
      email: str


  class UserRegistered(BaseModel):
      id: UUID
      email: str
      workspace_id: UUID
      officeclaw_token: str
      created_at: datetime


  class BootstrapOut(BaseModel):
      workspace_id: UUID
      officeclaw_token: str
  ```

- [ ] **Step 2: Update `api/src/identity/adapters/out/repository.py`**

  Remove `set_token` and `find_by_token` — those now live in WorkspaceRepo:

  ```python
  from uuid import UUID
  import asyncpg


  class UserRepo:
      def __init__(self, conn: asyncpg.Pool) -> None:
          self._conn = conn

      async def create(self, email: str) -> asyncpg.Record:
          return await self._conn.fetchrow(
              'INSERT INTO "user" (email) VALUES ($1) RETURNING *', email
          )

      async def find_by_id(self, user_id: UUID) -> asyncpg.Record | None:
          return await self._conn.fetchrow(
              'SELECT * FROM "user" WHERE id = $1', user_id
          )

      async def find_by_email(self, email: str) -> asyncpg.Record | None:
          return await self._conn.fetchrow(
              'SELECT * FROM "user" WHERE email = $1', email
          )
  ```

- [ ] **Step 3: Update `api/src/identity/app/users.py`**

  `UserService` now depends on `WorkspaceApp` instead of `FleetApp` + `IntegrationsApp`. Bootstrap delegates entirely to workspace:

  ```python
  """UserService — identity app layer. Delegates bootstrap to WorkspaceApp."""
  from __future__ import annotations

  from typing import TYPE_CHECKING
  from uuid import UUID

  import asyncpg

  from src.identity.adapters.out.repository import UserRepo

  if TYPE_CHECKING:
      from src.workspace.app import WorkspaceApp


  class UserService:
      def __init__(self, user_repo: UserRepo, workspace: WorkspaceApp) -> None:
          self._users = user_repo
          self._workspace = workspace

      async def create(self, email: str) -> asyncpg.Record:
          return await self._users.create(email)

      async def find_by_id(self, user_id: UUID) -> asyncpg.Record | None:
          return await self._users.find_by_id(user_id)

      async def register(self, email: str) -> tuple[asyncpg.Record, asyncpg.Record]:
          """Create user + bootstrap default workspace. Returns (user_record, workspace_record)."""
          user = await self._users.create(email)
          workspace = await self._workspace.create_workspace(user["id"], "Personal")
          return user, workspace

      async def bootstrap(self, user_id: UUID) -> asyncpg.Record:
          """Bootstrap Personal workspace for a user created by better-auth. Returns workspace record."""
          user = await self._users.find_by_id(user_id)
          if not user:
              raise ValueError(f"User {user_id} not found")
          return await self._workspace.create_workspace(user_id, "Personal")
  ```

- [ ] **Step 4: Update `api/src/identity/app/__init__.py`**

  ```python
  from __future__ import annotations

  from typing import TYPE_CHECKING
  from uuid import UUID

  import asyncpg

  from src.identity.app.users import UserService

  if TYPE_CHECKING:
      from src.workspace.app import WorkspaceApp


  class IdentityApp:
      def __init__(self, service: UserService) -> None:
          self._service = service

      async def register(self, email: str) -> tuple[asyncpg.Record, asyncpg.Record]:
          return await self._service.register(email)

      async def find_by_id(self, user_id: UUID) -> asyncpg.Record | None:
          return await self._service.find_by_id(user_id)

      async def bootstrap(self, user_id: UUID) -> asyncpg.Record:
          return await self._service.bootstrap(user_id)
  ```

- [ ] **Step 5: Update `api/src/identity/adapters/_in/router.py`**

  ```python
  from uuid import UUID

  import asyncpg
  from fastapi import APIRouter, Depends, HTTPException, Request

  from src.identity.app import IdentityApp
  from src.identity.core.schema import BootstrapOut, UserCreate, UserRegistered

  router = APIRouter()


  def get_identity(request: Request) -> IdentityApp:
      return request.app.state.identity


  @router.post("", response_model=UserRegistered, status_code=201)
  async def create_user(
      body: UserCreate,
      identity: IdentityApp = Depends(get_identity),
  ) -> UserRegistered:
      try:
          user, workspace = await identity.register(body.email)
      except asyncpg.UniqueViolationError:
          raise HTTPException(409, "Email already registered")
      return UserRegistered(
          id=user["id"],
          email=user["email"],
          workspace_id=workspace["id"],
          officeclaw_token=workspace["officeclaw_token"],
          created_at=user["created_at"],
      )


  @router.post("/{user_id}/bootstrap", response_model=BootstrapOut, status_code=201)
  async def bootstrap_user(
      user_id: UUID,
      identity: IdentityApp = Depends(get_identity),
  ) -> BootstrapOut:
      """Called by SvelteKit after better-auth creates a new user."""
      try:
          workspace = await identity.bootstrap(user_id)
      except asyncpg.UniqueViolationError:
          raise HTTPException(409, "User already bootstrapped")
      except ValueError as e:
          raise HTTPException(404, str(e))
      return BootstrapOut(
          workspace_id=workspace["id"],
          officeclaw_token=workspace["officeclaw_token"],
      )
  ```

- [ ] **Step 6: Update `api/src/identity/di.py`**

  ```python
  from __future__ import annotations

  from typing import TYPE_CHECKING

  import asyncpg

  from src.identity.adapters.out.repository import UserRepo
  from src.identity.app import IdentityApp
  from src.identity.app.users import UserService

  if TYPE_CHECKING:
      from src.workspace.app import WorkspaceApp


  def build(pool: asyncpg.Pool, workspace: WorkspaceApp) -> IdentityApp:
      repo = UserRepo(pool)
      service = UserService(repo, workspace)
      return IdentityApp(service)
  ```

- [ ] **Step 7: Commit**

  ```bash
  git add api/src/identity/
  git commit -m "feat(identity): delegate bootstrap to WorkspaceApp, remove token from user"
  ```

---

## Task 10: Update MCP auth + knowledge domain — workspace_id

**Files:**
- Modify: `api/src/entrypoint/mcp/__init__.py`
- Modify: `api/src/entrypoint/mcp/agents.py`
- Modify: `api/src/entrypoint/mcp/envs.py`
- Modify: `api/src/entrypoint/mcp/channels.py`
- Modify: `api/src/entrypoint/mcp/mcp_servers.py`
- Modify: `api/src/entrypoint/mcp/skills.py`
- Modify: `api/src/entrypoint/mcp/templates.py`
- Modify: `api/src/entrypoint/mcp/knowledge.py`
- Modify: `api/src/knowledge/adapters/_in/router.py`
- Modify: `api/src/knowledge/app/service.py`
- Modify: `api/src/knowledge/core/ports/_in.py`

- [ ] **Step 1: Update `api/src/entrypoint/mcp/__init__.py`**

  Replace `_identity` with `_workspace` and rename `_require_user` → `_require_workspace`:

  ```python
  import logging
  from uuid import UUID

  import asyncpg
  from fastmcp import FastMCP
  from fastmcp.server.context import Context

  from src.fleet.app import FleetApp
  from src.workspace.app import WorkspaceApp
  from src.integrations.app import IntegrationsApp
  from src.knowledge.app import KnowledgeApp
  from src.library.app import LibraryApp

  logger = logging.getLogger(__name__)

  admin_mcp = FastMCP("OfficeClaw-Admin")
  knowledge_mcp = FastMCP("OfficeClaw-Knowledge")

  _pool: asyncpg.Pool | None = None
  _fleet: FleetApp | None = None
  _workspace: WorkspaceApp | None = None
  _library: LibraryApp | None = None
  _integrations: IntegrationsApp | None = None
  _knowledge: KnowledgeApp | None = None


  def setup(
      pool: asyncpg.Pool,
      fleet: FleetApp,
      workspace: WorkspaceApp,
      library: LibraryApp,
      integrations: IntegrationsApp,
      knowledge: KnowledgeApp,
  ) -> None:
      global _pool, _fleet, _workspace, _library, _integrations, _knowledge
      _pool = pool
      _fleet = fleet
      _workspace = workspace
      _library = library
      _integrations = integrations
      _knowledge = knowledge


  def _assert_ready() -> None:
      if _pool is None:
          raise RuntimeError("MCP not initialised — call setup() first")


  async def _require_workspace(context: Context) -> UUID:
      """Extract and validate bearer token → return workspace_id."""
      _assert_ready()
      request = context.request_context.request
      auth = request.headers.get("authorization", "")
      if not auth.lower().startswith("bearer "):
          raise ValueError("Missing or malformed Authorization header")
      token = auth[7:]
      assert _workspace is not None
      record = await _workspace.find_by_token(token)
      if not record:
          raise ValueError("Invalid OFFICECLAW_TOKEN")
      return record["id"]  # workspace id


  from . import agents, channels, envs, knowledge, mcp_servers, skills, templates  # noqa: E402, F401
  ```

- [ ] **Step 2: Update all MCP tool files**

  In `agents.py`, `envs.py`, `channels.py`, `mcp_servers.py`, `skills.py`, `templates.py`:
  - Replace `user_id = await _pkg._require_user(context)` → `workspace_id = await _pkg._require_workspace(context)`
  - Replace `user_id` variable with `workspace_id` in all fleet/integrations/library calls

  Example in `agents.py`:
  ```python
  @_pkg.admin_mcp.tool()
  async def get_fleet_status(context: Context) -> dict:
      workspace_id = await _pkg._require_workspace(context)
      _pkg._assert_ready()
      assert _pkg._fleet is not None
      records = await _pkg._fleet.list_agents(workspace_id)
      ...

  @_pkg.admin_mcp.tool()
  async def create_agent(context: Context, name: str, image: str = "localhost:5005/officeclaw/agent:latest") -> dict:
      workspace_id = await _pkg._require_workspace(context)
      _pkg._assert_ready()
      assert _pkg._fleet is not None
      record = await _pkg._fleet.create_agent(workspace_id, name, image, False)
      return {"id": str(record["id"]), "name": record["name"], "status": record["status"]}
  ```

- [ ] **Step 3: Update knowledge domain — `user_id` → `workspace_id`**

  In `api/src/knowledge/core/ports/_in.py`: replace `user_id: UUID` → `workspace_id: UUID` in `ingest`, `ingest_file`, `query`, `get_graph` signatures.

  In `api/src/knowledge/app/service.py`: same replacement in method signatures and internal calls.

  In `api/src/knowledge/adapters/_in/router.py`:
  - Rename `get_knowledge_user_id` → `get_knowledge_workspace_id`
  - Change token lookup: replace `identity.find_by_token(token)` with workspace lookup via `request.app.state.workspace.find_by_token(token)`
  - Return `record["id"]` (workspace id, not user id)

  ```python
  async def get_knowledge_workspace_id(request: Request) -> UUID:
      """Extract workspace_id from bearer token."""
      from src.workspace.app import WorkspaceApp
      workspace: WorkspaceApp = request.app.state.workspace
      auth = request.headers.get("authorization", "")
      if not auth.lower().startswith("bearer "):
          raise HTTPException(401, "Missing Authorization header")
      token = auth[7:]
      record = await workspace.find_by_token(token)
      if not record:
          raise HTTPException(401, "Invalid token")
      return record["id"]
  ```

  Update all route handlers to use `workspace_id: UUID = Depends(get_knowledge_workspace_id)`.

- [ ] **Step 4: Commit**

  ```bash
  git add api/src/entrypoint/mcp/ api/src/knowledge/
  git commit -m "feat(mcp,knowledge): replace user_id with workspace_id in MCP auth and knowledge domain"
  ```

---

## Task 11: Update test suite

**Files:**
- Modify: `api/tests/conftest.py`
- Modify: `api/tests/test_admin.py`
- Modify: `api/tests/test_agents.py`
- Modify: `api/tests/test_links.py`
- Modify: `api/tests/test_mcp_tools.py`

- [ ] **Step 1: Update `api/tests/conftest.py`**

  Add `workspace_di` import. Update `client` fixture to wire workspace domain. Update `mcp_user` fixture to return `workspace_id`. Add `workspace_deps` fixture:

  ```python
  # At top: add import
  import src.workspace.di as workspace_di

  # In client fixture: add after fleet build
  workspace = workspace_di.build(pool, fleet, integrations)  # type: ignore[arg-type]
  identity = identity_di.build(pool, workspace)  # type: ignore[arg-type]

  # Add workspace to app.state and mcp_setup
  app.state.workspace = workspace

  mcp_setup(
      pool=pool,  # type: ignore[arg-type]
      fleet=fleet,
      workspace=workspace,
      library=library,
      integrations=integrations,
  )

  # Update mcp_user fixture
  @pytest.fixture
  async def mcp_user(client):
      """Create a user and return (user_id, workspace_id, token)."""
      resp = await client.post("/users", json={"email": "mcp-user@example.com"})
      body = resp.json()
      return body["id"], body["workspace_id"], body["officeclaw_token"]

  # Update mcp_conn_user fixture
  @pytest.fixture
  async def mcp_conn_user(conn, mcp_user):
      user_id, workspace_id, _ = mcp_user
      return conn, UUID(workspace_id)

  # Add workspace_deps fixture
  @pytest.fixture
  def workspace_deps(conn, fleet_deps, integrations_deps):
      return workspace_di.build(conn, fleet_deps, integrations_deps)  # type: ignore[arg-type]
  ```

- [ ] **Step 2: Update `api/tests/test_admin.py`**

  All tests that do `uid = UUID(resp.json()["id"]); agents = await fleet_deps.list_agents(uid)` must use `workspace_id` instead:

  ```python
  async def test_create_user_creates_admin_agent(client, fleet_deps):
      resp = await client.post("/users", json={"email": "admin-agent@example.com"})
      workspace_id = UUID(resp.json()["workspace_id"])
      agents = await fleet_deps.list_agents(workspace_id)
      admin_agents = [a for a in agents if a["is_admin"]]
      assert len(admin_agents) == 1
      assert admin_agents[0]["name"] == "Admin"

  async def test_admin_agent_has_seed_files(client, fleet_deps):
      resp = await client.post("/users", json={"email": "admin-files@example.com"})
      workspace_id = UUID(resp.json()["workspace_id"])
      agents = await fleet_deps.list_agents(workspace_id)
      agent_id = next(a["id"] for a in agents if a["is_admin"])
      files = await fleet_deps.list_files(agent_id)
      paths = {f["path"] for f in files}
      assert "SOUL.md" in paths

  # Same pattern for test_admin_agent_has_mcp_config and test_admin_agent_has_env_linked
  ```

  `test_create_user_returns_token` becomes:
  ```python
  async def test_create_user_returns_token(client):
      resp = await client.post("/users", json={"email": "admin-test@example.com"})
      assert resp.status_code == 201
      body = resp.json()
      assert "officeclaw_token" in body
      assert "workspace_id" in body
      assert len(body["officeclaw_token"]) > 20
  ```

- [ ] **Step 3: Update `api/tests/test_agents.py`**

  Replace `user_id` fixture with `workspace_id` fixture:

  ```python
  @pytest.fixture
  async def workspace_id(client):
      resp = await client.post("/users", json={"email": "agent-owner@example.com"})
      return resp.json()["workspace_id"]


  async def test_create_agent(client, workspace_id):
      resp = await client.post("/agents", json={"workspace_id": workspace_id, "name": "My Agent"})
      assert resp.status_code == 201
      body = resp.json()
      assert body["name"] == "My Agent"
      assert body["status"] == "idle"
      assert body["is_admin"] is False


  async def test_list_agents_for_user(client, workspace_id, fleet_deps):
      await client.post("/agents", json={"workspace_id": workspace_id, "name": "A1"})
      await client.post("/agents", json={"workspace_id": workspace_id, "name": "A2"})
      agents = await fleet_deps.list_agents(UUID(workspace_id))
      # bootstrap creates 1 Admin; 2 more added above = 3 total
      assert len(agents) == 3
  ```

  Keep `test_update_agent_status` and `test_delete_agent` unchanged (they use `agent_id`, not `user_id`).

- [ ] **Step 4: Update `api/tests/test_links.py` and `api/tests/test_mcp_tools.py`**

  Find all uses of `user_id` from user creation responses and replace with `workspace_id`. Find all calls to `create_env(user_id, ...)`, `create_channel(user_id, ...)` etc. and replace with `workspace_id`.

  Also in `test_mcp_tools.py`:
  - `mcp_user` fixture now returns `(user_id, workspace_id, token)` — unpack accordingly:
    ```python
    @pytest.fixture
    async def mcp_user(client):
        user_id, workspace_id, token = mcp_user_tuple  # from conftest
        return workspace_id, token  # tools only need workspace_id + token
    ```

- [ ] **Step 5: Run all tests**

  ```bash
  cd api && python -m pytest tests/ -v 2>&1 | tail -30
  ```

  Expected: all tests pass. If any fail, read the error and fix before continuing.

- [ ] **Step 6: Commit**

  ```bash
  git add api/tests/
  git commit -m "test: update test suite for workspace_id ownership model"
  ```

---

## Task 12: Web — Drizzle schema + auth.ts

**Files:**
- Modify: `web/src/lib/server/db/auth.schema.ts`
- Modify: `web/src/lib/server/db/app.schema.ts`
- Modify: `web/src/lib/server/auth.ts`

- [ ] **Step 1: Update `web/src/lib/server/db/auth.schema.ts`**

  Remove `officeclawToken` field from the `user` table definition:

  ```typescript
  export const user = pgTable('user', {
    id: uuid('id').primaryKey().defaultRandom(),
    name: text('name').notNull().default(''),
    email: text('email').notNull().unique(),
    emailVerified: boolean('email_verified').notNull().default(false),
    image: text('image'),
    createdAt: timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
    updatedAt: timestamp('updated_at', { withTimezone: true })
      .notNull()
      .defaultNow()
      .$onUpdate(() => new Date())
    // officeclawToken removed: lives on workspaces now
  });
  ```

- [ ] **Step 2: Update `web/src/lib/server/db/app.schema.ts`**

  Add `workspaces` table. Rename `userEnvs` → `workspaceEnvs`, `userChannels` → `workspaceChannels`, `userMcp` → `workspaceMcp`, `userTemplates` → `workspaceTemplates`. Replace `userId` FK → `workspaceId` FK → `workspaces` on all app tables.

  Add the workspaces table after the user import:
  ```typescript
  export const workspaces = pgTable('workspaces', {
    id: uuid().defaultRandom().primaryKey().notNull(),
    userId: uuid('user_id')
      .notNull()
      .references(() => user.id, { onDelete: 'cascade' }),
    name: text().notNull(),
    officeclawToken: text('officeclaw_token').unique(),
    createdAt: timestamp('created_at', { withTimezone: true }).defaultNow().notNull()
  });
  ```

  Update `agents` table:
  ```typescript
  export const agents = pgTable('agents', {
    id: uuid().defaultRandom().primaryKey().notNull(),
    workspaceId: uuid('workspace_id')
      .notNull()
      .references(() => workspaces.id, { onDelete: 'cascade' }),
    // ... rest unchanged
  });
  ```

  Rename and update `userEnvs` → `workspaceEnvs`:
  ```typescript
  export const workspaceEnvs = pgTable(
    'workspace_envs',
    {
      id: uuid().defaultRandom().primaryKey().notNull(),
      workspaceId: uuid('workspace_id')
        .notNull()
        .references(() => workspaces.id, { onDelete: 'cascade' }),
      name: text().notNull(),
      category: text(),
      createdAt: timestamp('created_at', { withTimezone: true }).defaultNow().notNull()
    },
    (t) => [unique('workspace_envs_workspace_id_name_key').on(t.workspaceId, t.name)]
  );
  ```

  Apply same pattern to `workspaceChannels`, `workspaceMcp`, `workspaceTemplates`. Update `agentEnvs`, `agentChannels`, `agentMcp` FK references to point to renamed tables. Update all `relations()` to use `workspaceId` and the new table names.

  Update `agentEnvs` FK:
  ```typescript
  envId: uuid('env_id')
    .notNull()
    .references(() => workspaceEnvs.id, { onDelete: 'cascade' })
  ```

  Update `agentChannels` FK:
  ```typescript
  channelId: uuid('channel_id')
    .notNull()
    .references(() => workspaceChannels.id, { onDelete: 'cascade' })
  ```

  Update `agentMcp` FK:
  ```typescript
  mcpId: uuid('mcp_id')
    .notNull()
    .references(() => workspaceMcp.id, { onDelete: 'cascade' })
  ```

  Update `agentUserTemplates` FK:
  ```typescript
  userTemplateId: uuid('user_template_id')
    .notNull()
    .references(() => workspaceTemplates.id, { onDelete: 'cascade' })
  ```

  Update all `relations()` accordingly (replace `user` relation with `workspace` relation, update field names).

- [ ] **Step 3: Update `web/src/lib/server/db/schema.ts`**

  Update barrel exports to include `workspaces` and renamed tables:

  ```typescript
  export * from './auth.schema';
  export * from './app.schema';
  ```

  (This file likely already re-exports everything — verify it still compiles after the renames.)

- [ ] **Step 4: Update `web/src/lib/server/auth.ts`**

  Remove `officeclawToken` from `user.additionalFields`. The `databaseHooks.user.create.after` still calls the bootstrap endpoint — the response now includes `workspace_id` and `officeclaw_token` but the hook doesn't need to use them:

  ```typescript
  export const auth = betterAuth({
    // ... same as before
    databaseHooks: {
      user: {
        create: {
          after: async (user) => {
            await fetch(`${env.API_URL}/users/${user.id}/bootstrap`, {
              method: 'POST'
            }).catch((err) => {
              console.error('[auth] bootstrap failed for user', user.id, err);
            });
          }
        }
      }
    },
    // Remove the user.additionalFields block entirely
    plugins: [
      emailOTP({ ... }),
      sveltekitCookies(getRequestEvent)
    ]
  });
  ```

- [ ] **Step 5: Check TypeScript compilation**

  ```bash
  cd web && pnpm check 2>&1 | head -40
  ```

  Fix any type errors from renamed imports (e.g., `userEnvs` → `workspaceEnvs` in load functions).

- [ ] **Step 6: Commit**

  ```bash
  git add web/src/lib/server/db/ web/src/lib/server/auth.ts
  git commit -m "feat(web): update Drizzle schema for workspaces, remove officeclawToken from user"
  ```

---

## Task 13: Web — URL routing `/w/[workspaceId]/` + layout update

**Files:**
- Modify: `web/src/routes/(app)/+layout.server.ts`
- Modify: `web/src/routes/(app)/+page.server.ts`
- Create: `web/src/routes/(app)/w/[workspaceId]/+layout.server.ts`
- Create: `web/src/routes/(app)/w/[workspaceId]/+page.server.ts`
- Move: `(app)/agents/` → `(app)/w/[workspaceId]/agents/`
- Move: `(app)/workspace/` → `(app)/w/[workspaceId]/workspace/`
- Move: `(app)/prompts/` → `(app)/w/[workspaceId]/prompts/`

- [ ] **Step 1: Update `web/src/routes/(app)/+layout.server.ts`**

  This layout now loads the user's workspace list (not workspace-specific data). Workspace-specific data moves to the `[workspaceId]` sub-layout:

  ```typescript
  import { redirect } from '@sveltejs/kit';
  import { db } from '$lib/server/db';
  import { workspaces } from '$lib/server/db/app.schema';
  import { eq } from 'drizzle-orm';
  import type { LayoutServerLoad } from './$types';

  export const load: LayoutServerLoad = async ({ locals }) => {
    if (!locals.session) redirect(302, '/auth');

    const userId = locals.user!.id;

    const userWorkspaces = await db
      .select()
      .from(workspaces)
      .where(eq(workspaces.userId, userId))
      .orderBy(workspaces.createdAt);

    return {
      user: locals.user!,
      session: locals.session!,
      workspaces: userWorkspaces
    };
  };
  ```

- [ ] **Step 2: Update `web/src/routes/(app)/+page.server.ts`**

  Redirect to the first (oldest) workspace:

  ```typescript
  import { redirect } from '@sveltejs/kit';
  import { db } from '$lib/server/db';
  import { workspaces } from '$lib/server/db/app.schema';
  import { eq } from 'drizzle-orm';
  import type { PageServerLoad } from './$types';

  export const load: PageServerLoad = async ({ locals }) => {
    const [first] = await db
      .select({ id: workspaces.id })
      .from(workspaces)
      .where(eq(workspaces.userId, locals.user!.id))
      .orderBy(workspaces.createdAt)
      .limit(1);

    if (first) redirect(302, `/w/${first.id}`);

    // No workspaces yet — bootstrap is still running
    return {};
  };
  ```

- [ ] **Step 3: Create `web/src/routes/(app)/w/[workspaceId]/+layout.server.ts`**

  Validates workspace ownership, loads workspace-specific sidebar data:

  ```typescript
  import { error } from '@sveltejs/kit';
  import { db } from '$lib/server/db';
  import {
    agents,
    workspaces,
    skills,
    workspaceEnvs,
    workspaceChannels,
    workspaceMcp,
    workspaceTemplates
  } from '$lib/server/db/app.schema';
  import { and, eq, ne, desc, count } from 'drizzle-orm';
  import type { LayoutServerLoad } from './$types';

  export const load: LayoutServerLoad = async ({ locals, params }) => {
    const workspaceId = params.workspaceId;

    // Validate ownership
    const [workspace] = await db
      .select()
      .from(workspaces)
      .where(and(eq(workspaces.id, workspaceId), eq(workspaces.userId, locals.user!.id)))
      .limit(1);

    if (!workspace) error(403, 'Workspace not found');

    const [userAgents, [skillsCount], [envsCount], [channelsCount], [mcpCount], [promptsCount]] =
      await Promise.all([
        db
          .select()
          .from(agents)
          .where(eq(agents.workspaceId, workspaceId))
          .orderBy(desc(agents.isAdmin), desc(agents.createdAt)),
        db.select({ n: count() }).from(skills).where(eq(skills.workspaceId, workspaceId)),
        db.select({ n: count() }).from(workspaceEnvs).where(eq(workspaceEnvs.workspaceId, workspaceId)),
        db.select({ n: count() }).from(workspaceChannels).where(eq(workspaceChannels.workspaceId, workspaceId)),
        db.select({ n: count() }).from(workspaceMcp).where(eq(workspaceMcp.workspaceId, workspaceId)),
        db
          .select({ n: count() })
          .from(workspaceTemplates)
          .where(
            and(
              eq(workspaceTemplates.workspaceId, workspaceId),
              ne(workspaceTemplates.templateType, 'user')
            )
          )
      ]);

    return {
      workspace,
      agents: userAgents,
      workspaceCounts: {
        skills: skillsCount?.n ?? 0,
        envs: envsCount?.n ?? 0,
        channels: channelsCount?.n ?? 0,
        mcp: mcpCount?.n ?? 0,
        knowledge: 0,
        prompts: promptsCount?.n ?? 0
      }
    };
  };
  ```

- [ ] **Step 4: Create `web/src/routes/(app)/w/[workspaceId]/+page.server.ts`**

  Redirect to the Admin agent in this workspace:

  ```typescript
  import { redirect } from '@sveltejs/kit';
  import { db } from '$lib/server/db';
  import { agents } from '$lib/server/db/app.schema';
  import { and, eq } from 'drizzle-orm';
  import type { PageServerLoad } from './$types';

  export const load: PageServerLoad = async ({ params }) => {
    const [admin] = await db
      .select({ id: agents.id })
      .from(agents)
      .where(and(eq(agents.workspaceId, params.workspaceId), eq(agents.isAdmin, true)))
      .limit(1);

    if (admin) redirect(302, `/w/${params.workspaceId}/agents/${admin.id}`);

    return {};
  };
  ```

- [ ] **Step 5: Move route directories**

  ```bash
  mkdir -p web/src/routes/\(app\)/w/\[workspaceId\]
  mv web/src/routes/\(app\)/agents web/src/routes/\(app\)/w/\[workspaceId\]/agents
  mv web/src/routes/\(app\)/workspace web/src/routes/\(app\)/w/\[workspaceId\]/workspace
  mv web/src/routes/\(app\)/prompts web/src/routes/\(app\)/w/\[workspaceId\]/prompts
  ```

- [ ] **Step 6: Update internal links in moved page files**

  After moving, any hardcoded links like `/agents/${id}` must become `/w/${workspaceId}/agents/${id}`. Search for these patterns:

  ```bash
  grep -r '"/agents/' web/src/routes/\(app\)/w --include="*.svelte" --include="*.ts"
  grep -r '"/workspace/' web/src/routes/\(app\)/w --include="*.svelte" --include="*.ts"
  ```

  Update each occurrence to include `/w/${params.workspaceId}` or `/w/${page.params.workspaceId}` prefix.

- [ ] **Step 7: Update `(app)/+page.svelte`**

  The root page.svelte under `(app)/` can remain as a simple loading screen (the server redirect handles it):

  ```svelte
  <p style="padding: 2rem; font-family: monospace; opacity: 0.5">Loading workspace…</p>
  ```

- [ ] **Step 8: Update load functions in moved page files**

  The moved `agents/[id]/+page.server.ts`, `workspace/environments/+page.server.ts` etc. reference `locals.user!.id` to query data. They must switch to `params.workspaceId`. Example for `agents/[id]/+page.server.ts`:

  ```typescript
  // Before: eq(agents.userId, locals.user!.id)
  // After: data comes from parent layout — workspaceId is in params
  ```

  Each moved server file: read it, check if it queries by `userId`, and update to `workspaceId` from params.

- [ ] **Step 9: Check TypeScript compilation**

  ```bash
  cd web && pnpm check 2>&1 | head -50
  ```

  Fix errors.

- [ ] **Step 10: Commit**

  ```bash
  git add web/src/routes/
  git commit -m "feat(web): restructure routes under /w/[workspaceId]/"
  ```

---

## Task 14: Web — API routes workspace_id + workspace switcher UI

**Files:**
- Modify: `web/src/routes/api/agents/+server.ts`
- Modify: `web/src/routes/(app)/+layout.svelte`
- Create: `web/src/lib/components/workspace-switcher.svelte`

- [ ] **Step 1: Update `web/src/routes/api/agents/+server.ts`**

  Pass `workspace_id` from request body instead of `user_id` from session:

  ```typescript
  export const POST: RequestHandler = async ({ request, locals }) => {
    if (!locals.session) error(401, 'Unauthorized');

    const body = await request.json();
    const name = body.name?.toString().trim();
    const workspaceId = body.workspace_id?.toString();

    if (!name) error(400, 'Name is required');
    if (!workspaceId) error(400, 'workspace_id is required');

    const upstream = await fetch(`${API_URL}/agents`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        workspace_id: workspaceId,
        name,
        image: body.image ?? 'localhost:5005/officeclaw/agent:latest',
        is_admin: false
      })
    });

    if (!upstream.ok) {
      const text = await upstream.text();
      error(upstream.status, text || 'Failed to create agent');
    }

    return json(await upstream.json(), { status: 201 });
  };
  ```

- [ ] **Step 2: Update `(app)/+layout.svelte` spawn agent call**

  The `createAgent` function sends to `/api/agents`. It must now include `workspace_id`. The layout gets `workspace` from the `[workspaceId]` sub-layout via `data`. Add `workspace_id: data.workspace?.id` to the fetch body:

  In the `createAgent` function:
  ```typescript
  body: JSON.stringify({ name, workspace_id: data.workspace?.id })
  ```

  Also update the `goto` after creation:
  ```typescript
  goto(`/w/${data.workspace?.id}/agents/${agent.id}`);
  ```

- [ ] **Step 3: Create `web/src/lib/components/workspace-switcher.svelte`**

  ```svelte
  <script lang="ts">
    import { goto } from '$app/navigation';
    import { Icon } from '$lib/icons';

    interface Workspace {
      id: string;
      name: string;
    }

    let { workspaces, activeWorkspaceId }: { workspaces: Workspace[]; activeWorkspaceId: string } =
      $props();

    let open = $state(false);
    let creating = $state(false);
    let newName = $state('');
    let loading = $state(false);
    let nameInput: HTMLInputElement | null = $state(null);

    const active = $derived(workspaces.find((w) => w.id === activeWorkspaceId));

    function toggle() {
      open = !open;
      if (!open) creating = false;
    }

    function startCreate() {
      creating = true;
      newName = '';
      setTimeout(() => nameInput?.focus(), 0);
    }

    async function createWorkspace() {
      const name = newName.trim();
      if (!name || loading) return;
      loading = true;
      try {
        const res = await fetch('/api/workspaces', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name })
        });
        if (!res.ok) return;
        const ws = await res.json();
        open = false;
        creating = false;
        goto(`/w/${ws.id}`);
      } finally {
        loading = false;
      }
    }

    function onKey(e: KeyboardEvent) {
      if (e.key === 'Enter') createWorkspace();
      if (e.key === 'Escape') { creating = false; open = false; }
    }
  </script>

  <div class="switcher">
    <button class="trigger font-mono" onclick={toggle} type="button">
      <span class="ws-initial">{active?.name?.[0]?.toUpperCase() ?? '?'}</span>
      <span class="ws-name">{active?.name ?? 'workspace'}</span>
      <Icon icon="tabler:chevron-up-down" width={12} height={12} class="chevron" />
    </button>

    {#if open}
      <div class="popover">
        <ul class="ws-list">
          {#each workspaces as ws (ws.id)}
            <li>
              <button
                class="ws-item font-mono"
                class:active={ws.id === activeWorkspaceId}
                onclick={() => { goto(`/w/${ws.id}`); open = false; }}
                type="button"
              >
                <span class="ws-initial sm">{ws.name[0]?.toUpperCase()}</span>
                {ws.name}
                {#if ws.id === activeWorkspaceId}
                  <Icon icon="tabler:check" width={11} height={11} class="check" />
                {/if}
              </button>
            </li>
          {/each}
        </ul>

        <div class="divider"></div>

        {#if creating}
          <div class="create-form">
            <input
              bind:this={nameInput}
              bind:value={newName}
              onkeydown={onKey}
              placeholder="workspace name…"
              class="create-input font-mono"
              maxlength={64}
              disabled={loading}
            />
            <button class="create-confirm font-mono" onclick={createWorkspace} disabled={!newName.trim() || loading} type="button">
              {loading ? 'creating…' : 'create ↵'}
            </button>
          </div>
        {:else}
          <button class="new-btn font-mono" onclick={startCreate} type="button">
            <Icon icon="tabler:plus" width={11} height={11} />
            new workspace
          </button>
        {/if}
      </div>
    {/if}
  </div>

  <style>
    .switcher {
      position: relative;
    }

    .trigger {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      width: 100%;
      padding: 0.55rem 0.75rem;
      font-size: 0.72rem;
      color: var(--sidebar-foreground);
      border-top: 1px solid var(--sidebar-border);
      transition: background 150ms ease;
    }

    .trigger:hover {
      background: var(--sidebar-accent);
    }

    .ws-initial {
      width: 20px;
      height: 20px;
      border-radius: 4px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.62rem;
      font-weight: 700;
      background: color-mix(in oklch, var(--primary) 18%, transparent);
      color: var(--primary);
      flex-shrink: 0;
    }

    .ws-initial.sm {
      width: 16px;
      height: 16px;
      font-size: 0.55rem;
      border-radius: 3px;
    }

    .ws-name {
      flex: 1;
      text-align: left;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    :global(.chevron) {
      color: color-mix(in oklch, var(--sidebar-foreground) 35%, transparent);
      flex-shrink: 0;
    }

    .popover {
      position: absolute;
      bottom: calc(100% + 4px);
      left: 0.5rem;
      right: 0.5rem;
      background: var(--sidebar);
      border: 1px solid var(--sidebar-border);
      border-radius: 0.4rem;
      box-shadow: 0 4px 16px rgba(0,0,0,0.25);
      overflow: hidden;
      z-index: 50;
    }

    .ws-list {
      list-style: none;
      padding: 0.3rem;
    }

    .ws-item {
      display: flex;
      align-items: center;
      gap: 0.45rem;
      width: 100%;
      padding: 0.35rem 0.5rem;
      font-size: 0.72rem;
      border-radius: 0.25rem;
      color: var(--sidebar-foreground);
      transition: background 120ms ease;
    }

    .ws-item:hover {
      background: var(--sidebar-accent);
    }

    .ws-item.active {
      color: var(--primary);
    }

    :global(.check) {
      margin-left: auto;
      color: var(--primary);
    }

    .divider {
      height: 1px;
      background: var(--sidebar-border);
      margin: 0 0.3rem;
    }

    .new-btn {
      display: flex;
      align-items: center;
      gap: 0.4rem;
      width: 100%;
      padding: 0.45rem 0.8rem;
      font-size: 0.68rem;
      color: color-mix(in oklch, var(--sidebar-foreground) 55%, transparent);
      transition: color 120ms ease, background 120ms ease;
    }

    .new-btn:hover {
      color: var(--sidebar-foreground);
      background: var(--sidebar-accent);
    }

    .create-form {
      padding: 0.5rem 0.6rem;
      display: flex;
      gap: 0.4rem;
      align-items: center;
    }

    .create-input {
      flex: 1;
      background: transparent;
      border: none;
      outline: none;
      font-size: 0.72rem;
      color: var(--sidebar-foreground);
    }

    .create-input::placeholder {
      color: color-mix(in oklch, var(--sidebar-foreground) 35%, transparent);
    }

    .create-confirm {
      font-size: 0.62rem;
      color: var(--primary);
      white-space: nowrap;
    }

    .create-confirm:disabled {
      opacity: 0.35;
      cursor: not-allowed;
    }
  </style>
  ```

- [ ] **Step 4: Add `/api/workspaces` route**

  Create `web/src/routes/api/workspaces/+server.ts`:

  ```typescript
  import { error, json } from '@sveltejs/kit';
  import type { RequestHandler } from './$types';

  const API_URL = process.env.API_URL ?? 'http://localhost:8000';

  export const POST: RequestHandler = async ({ request, locals }) => {
    if (!locals.session) error(401, 'Unauthorized');

    const body = await request.json();
    const name = body.name?.toString().trim();
    if (!name) error(400, 'Name is required');

    const upstream = await fetch(`${API_URL}/workspaces`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: locals.user!.id, name })
    });

    if (!upstream.ok) {
      const text = await upstream.text();
      error(upstream.status, text || 'Failed to create workspace');
    }

    return json(await upstream.json(), { status: 201 });
  };
  ```

- [ ] **Step 5: Add WorkspaceSwitcher to `(app)/+layout.svelte`**

  Import and add the switcher between the theme row and user footer. It receives `workspaces` from the layout data and `activeWorkspaceId` from page params:

  ```svelte
  <script lang="ts">
    import WorkspaceSwitcher from '$lib/components/workspace-switcher.svelte';
    // ... existing imports

    let { data, children } = $props();
    const workspaceId = $derived(page.params.workspaceId as string | undefined);
  </script>

  <!-- In the sidebar, between theme-row and user-footer: -->
  <WorkspaceSwitcher
    workspaces={data.workspaces ?? []}
    activeWorkspaceId={workspaceId ?? ''}
  />
  ```

- [ ] **Step 6: Check TypeScript compilation and start dev server**

  ```bash
  cd web && pnpm check 2>&1 | head -50
  ```

  Fix errors, then:
  ```bash
  pnpm dev
  ```

  Verify: visit `http://localhost:5173` → should redirect to `/w/[workspaceId]/` → Admin agent chat. Workspace switcher appears at bottom of sidebar.

- [ ] **Step 7: Commit**

  ```bash
  git add web/src/
  git commit -m "feat(web): add workspace switcher, update API routes to use workspace_id"
  ```

---

## Self-Review Checklist (run before calling done)

- [ ] `api/migrations/versions/001_initial_schema.sql` has no `user_id` in app tables
- [ ] `api/src/workspace/` domain exists with all files
- [ ] `python -m pytest api/tests/ -v` — all tests pass
- [ ] `pnpm check` in `web/` — no type errors
- [ ] `pnpm dev` — app loads, workspace redirect works, switcher visible
- [ ] Workspace creation from switcher creates new workspace and navigates to it
- [ ] No `user_id` references remain in Python app tables (search: `grep -r "user_id" api/src --include="*.py" | grep -v "\"user\"" | grep -v conftest`)
