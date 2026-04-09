# OfficeClaw — Architecture Design

**Date:** 2026-04-09  
**Status:** Approved  

---

## Overview

OfficeClaw is an open-source control plane for managing a fleet of personal AI agents. Each agent is described declaratively (nanobot workspace files), runs in an isolated microVM, and is managed through a web dashboard and an agentic Admin interface.

---

## System Components

Four services in a monorepo:

```
officeclaw/
  api/               # Python / FastAPI + asyncpg  — control plane, migrations
  sandbox-manager/   # TypeScript + microsandbox SDK — VM lifecycle
  mcp/               # Python MCP server — OfficeClaw as MCP (officeclaw MCP)
  web/               # SvelteKit — dashboard UI
```

### api/ — Python / FastAPI
- REST API + WebSocket endpoints
- Owns all Postgres migrations (asyncpg)
- Generates nanobot `config.json` at VM start
- Proxies Web UI chat to Admin VM's nanobot gateway

### sandbox-manager/ — TypeScript
- Thin HTTP service wrapping microsandbox SDK
- Endpoints: `POST /sandbox/create`, `POST /sandbox/stop`, `GET /sandbox/:id/status`
- Receives all files and env vars in the request body — no direct DB access
- Writes workspace files into VM volume, starts `nanobot gateway`

### mcp/ — Python MCP server
- HTTP/SSE MCP server, exposes OfficeClaw API as tools
- Auth via per-user `OFFICECLAW_TOKEN` — all operations scoped to user_id
- Tools: `list_agents`, `create_agent`, `update_agent_file`, `start_agent`, `stop_agent`, `delete_agent`, `list_skills`, `create_skill`, `attach_skill`, `list_envs`, `create_env`, `list_channels`, `get_fleet_status`
- Calls `api/` REST endpoints internally — does not touch DB directly

### web/ — SvelteKit
- Agent list, file editor (workspace files), status, channel config
- WebSocket for Admin chat (proxied to Admin VM nanobot gateway)
- Reads file tree and contents via `api/` — full observability into every agent's workspace

---

## Agent Runtime

- **VM**: microsandbox microVM, boots <100ms, OCI-compatible
- **Agent runtime**: nanobot (`nanobot gateway`) running inside VM
- **Workspace**: nanobot standard — `SOUL.md`, `AGENTS.md`, `TOOLS.md`, `HEARTBEAT.md`, `USER.md`, `memory/MEMORY.md`, `memory/history.jsonl`, `cron/jobs.json`, `skills/<name>/SKILL.md`

### VM Start Sequence

```
api reads from Postgres:
  1. agent_files       → workspace files content
  2. agent_skills      → skill directories (skill_files per skill)
  3. agent_envs        → merge all values → env vars
  4. agent_channels    → channel configs for config.json
  5. agent_mcp         → MCP servers for config.json

api generates config.json (nanobot standard):
  - agents.defaults.workspace = /workspace
  - providers section      ← from env values (uses ${VAR} interpolation)
  - channels section       ← from agent_channels
  - tools.mcpServers       ← from agent_mcp

api POSTs to sandbox-manager:
  { files: [{path, content}], env: {KEY: VALUE}, config_json: {...} }

sandbox-manager:
  - Sandbox.create(image, volumes)
  - sandbox.fs().write() for each file
  - writes config.json to /root/.nanobot/config.json
  - sandbox.shellStream("nanobot gateway") → streams logs
```

### VM Stop Sequence

```
sandbox-manager reads known mutable paths from VM volume:
  sandbox.fs().readString("workspace/memory/MEMORY.md")
  sandbox.fs().readString("workspace/memory/history.jsonl")
  sandbox.fs().readString("workspace/cron/jobs.json")
  → returns {path, content} list to api/

api writes updated content back to agent_files in Postgres
sandbox.stopAndWait()
agent.status → idle
```

---

## Database Schema

```sql
-- Core
users          (id uuid PK, email text UNIQUE, created_at)

-- Agent fleet
agents         (id uuid PK, user_id FK, name text, status enum(idle/running/error),
                sandbox_id text nullable, image text, is_admin bool default false,
                created_at, updated_at)

agent_files    (id uuid PK, agent_id FK, path text, content text, updated_at)
               -- paths: SOUL.md, AGENTS.md, TOOLS.md, HEARTBEAT.md, USER.md,
               --        memory/MEMORY.md, memory/history.jsonl, cron/jobs.json

-- User skill library
skills         (id uuid PK, user_id FK, name text, description text, created_at)
skill_files    (id uuid PK, skill_id FK, path text, content text, updated_at)
               -- paths: SKILL.md, scripts/*, README.md, ...

-- Named env configs (BYOK)
user_envs      (id uuid PK, user_id FK, name text,
                values jsonb ENCRYPTED, created_at)
               -- e.g. name='anthropic', values={ANTHROPIC_API_KEY: '...'}

-- Channel integrations
user_channels  (id uuid PK, user_id FK, type text,  -- telegram/discord/...
                config jsonb ENCRYPTED, created_at)
               -- config: {token: '...', allow_from: ['userid123']}

-- MCP servers per agent
agent_mcp      (id uuid PK, agent_id FK, name text, config jsonb ENCRYPTED)
               -- config: {command, args} or {url, headers} — headers may contain auth tokens

-- Many-to-many links
agent_skills   (agent_id FK, skill_id FK)
agent_envs     (agent_id FK, env_id FK)
agent_channels (agent_id FK, channel_id FK)
```

### Secrets
- `user_envs.values` and `user_channels.config` encrypted at application level (AES) before storage
- Never returned in API responses — write-only from UI perspective (show/hide like GitHub secrets)
- Injected into VM as env vars; `config.json` uses `${VAR}` interpolation

---

## File Storage

Interface `FileStorage` with two backends:
- **PostgresFileStorage** — MVP: files stored as `text` in `agent_files` and `skill_files`
- **S3FileStorage** — future: metadata in Postgres, content in S3/MinIO

Switching via config — no code changes. Self-hosted = Postgres only. Cloud = Postgres + S3.

---

## Admin Agent

Every user gets an Admin agent created at registration (`is_admin=true`).

**What it does:** Manages the user's entire fleet via natural language — creates agents, installs skills, configures channels, starts/stops VMs.

**Runtime:** nanobot in microsandbox (same abstraction as all other agents).

**MCP tools mounted:**
- `officeclaw` MCP → fleet management (CRUD on agents, skills, envs)
- `clawhub` CLI/MCP → search and install skills from the public registry (separate project, mounted as MCP tool)

**Registration flow:**
1. Create `users` record
2. Generate `OFFICECLAW_TOKEN` → store in `user_envs`
3. Create `agents` record with `is_admin=true`
4. Seed `agent_files`: `SOUL.md` (fleet manager persona), `AGENTS.md`, `TOOLS.md`
5. Add `agent_mcp`: officeclaw + clawhub
6. Start Admin VM → user can immediately chat via Web UI

**Web UI chat:** `web/ → api/ WebSocket → nanobot gateway (Admin VM)` — streaming proxy.

---

## CRON

MVP: cron runs only while VM is running.

- `HEARTBEAT.md` — edited via UI, stored in `agent_files`, nanobot polls every 30 min
- `cron/jobs.json` — full cron expressions, stored in `agent_files`, editable via file editor in UI
- Both synced to VM volume at start; `memory/` and `cron/jobs.json` synced back to Postgres at stop

v2 (future): scheduler in `api/` wakes VM at cron time, runs, stops.

---

## Observability

Not built in-house — leverage existing tools:
- **LLM traces**: nanobot → OpenTelemetry → Langfuse
- **Raw logs**: nanobot stdout → POST `/logs` endpoint in `api/`
- **API logs**: structured logging via structlog/uvicorn
- **Web UI**: file tree + content viewer for every agent's workspace (reads via `api/`)

No `run_logs` table in MVP.

---

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| VM runtime | microsandbox | <100ms boot, OCI-compatible, named volumes |
| Agent runtime | nanobot | workspace standard, channels, cron built-in |
| File storage | Postgres (FileStorage abstraction) | Simple MVP, S3 switchable later |
| Secrets | app-level AES encryption in jsonb | No pgcrypto dependency, portable |
| Admin runtime | nanobot VM (same as other agents) | Consistent abstraction, dogfooding |
| Admin DB access | via officeclaw MCP → api/ REST | MCP stays thin, api/ owns auth/validation |
| Cron in MVP | files only (HEARTBEAT.md, cron/jobs.json) | No scheduler complexity until v2 |
| Logs | external (OTel + Langfuse) | Don't rebuild what exists |
| sandbox-manager | separate TS service | Isolates microsandbox SDK from Python api/ |
