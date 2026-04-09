# OfficeClaw — Project Context for Claude

## What This Is

OfficeClaw is an AI-agent fleet manager. Users sign up, get an "Admin" agent bootstrapped for them, and use that agent to create and manage a personal fleet of AI agents.

Stack: SvelteKit (web) + Python/FastAPI (api) + Postgres + Docker (sandbox containers via `msb` CLI).

---

## Architecture

### CQRS-lite

- **Reads**: SvelteKit `load` functions query Postgres directly via Drizzle ORM
- **Writes / business logic**: SvelteKit server actions call Python API over HTTP
- Never bypass this split — no writes from Drizzle, no reads from Python for UI concerns

### Auth

- **better-auth** owns the user lifecycle (registration, sessions, OAuth, OTP)
- better-auth tables (`user`, `session`, `account`, `verification`) live in Postgres alongside app tables
- `user.officeclaw_token` is a custom field — a Python-generated bearer token for MCP clients
- MCP auth uses `officeclaw_token` directly (queries `"user"` table) — completely separate from session cookies

### Bootstrap flow

1. better-auth creates a user row
2. `databaseHooks.user.create.after` in `web/src/lib/server/auth.ts` calls `POST /users/{id}/bootstrap`
3. Python generates `officeclaw_token`, creates Admin agent, wires up SOUL.md / AGENTS.md / TOOLS.md / MCP config

---

## Python API — Hexagonal Layout

Each domain (`fleet`, `identity`, `integrations`, `library`) has the same structure:

```
src/{domain}/
  core/
    schema.py          # Pydantic models (input/output)
    ports/
      _in.py           # Inbound port protocols (what the app layer offers)
      out.py           # Outbound port protocols (what the app layer needs)
  app/
    __init__.py        # Facade (e.g. FleetApp) — single entry point per domain
    *.py               # Use-case services
  adapters/
    _in/
      router.py        # FastAPI router — thin, delegates to app facade
    out/
      repository.py    # asyncpg implementations of out-port protocols
  di.py                # Wires concrete adapters into app services, returns facade
```

### Rules

- **Routers are thin**: validate input, call the domain facade, return Pydantic response — no business logic
- **Cross-domain calls go through facades**: `fleet.di` receives `IntegrationsApp` and `LibraryApp` — it never imports `integrations.adapters.out.repository` directly
- **App services depend on port protocols**, not concrete adapters — `AgentService(IAgentRepo, IAgentFileRepo)` not `AgentService(AgentRepo, AgentFileRepo)`
- **No asyncpg.Record leaking** past the app layer — facades return `dict` or Pydantic models, not raw DB rows
- App is wired in `src/entrypoint/main.py` `lifespan`: build order is `integrations → library → fleet → identity`

---

## Database

### Migrations

- **Single source of truth**: `api/migrations/versions/001_initial_schema.sql` (raw SQL, applied by Python)
- Drizzle **never runs migrations** — it is a read-only typed client in `web/`
- If schema changes: update the SQL migration AND `web/src/lib/server/db/auth.schema.ts` / `app.schema.ts`

### Key conventions

- `user` is a reserved word in Postgres — always quote it: `"user"`
- All app FK columns reference `"user"(id)` (UUID), not a separate `users` table
- `bytea` encrypted columns (`values_encrypted`, `config_encrypted`) exist in Postgres but are **excluded from Drizzle schema** — web never reads raw encrypted data

### Drizzle schema files

- `web/src/lib/server/db/auth.schema.ts` — mirrors better-auth tables (hand-maintained)
- `web/src/lib/server/db/app.schema.ts` — mirrors app domain tables
- `web/src/lib/server/db/schema.ts` — barrel export of both

---

## Env Variables

| Service | Key                       | Purpose                                   |
| ------- | ------------------------- | ----------------------------------------- |
| web     | `ORIGIN`                  | App base URL (used by better-auth)        |
| web     | `BETTER_AUTH_SECRET`      | Session signing secret                    |
| web     | `GOOGLE_CLIENT_ID/SECRET` | OAuth                                     |
| web     | `API_URL`                 | Python API base URL for server-side fetch |
| web     | `DATABASE_URL`            | Postgres (Drizzle reads)                  |
| api     | `DATABASE_URL`            | Postgres (asyncpg pool)                   |
| api     | `MCP_BASE_URL`            | Injected into Admin agent's MCP config    |

---

## What Not to Do

- Don't add a `users` table in Python — user rows are owned by better-auth in `"user"`
- Don't put business logic in routers or DI files
- Don't import a domain's concrete adapter from another domain
- Don't run `drizzle-kit push` or `drizzle-kit migrate` — migrations are Python's job
- Don't add CRUD routes to Python for data that SvelteKit can read via Drizzle
