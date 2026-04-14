# Workspaces Design

**Date:** 2026-04-14  
**Status:** Approved

## Summary

Introduce a `workspaces` table as the primary ownership unit for all fleet resources. A user can have multiple workspaces, each fully self-contained with its own agents, skills, envs, channels, MCP configs, templates, knowledge, and `officeclaw_token`. One user, many fleet contexts.

---

## 1. Schema

### New table: `workspaces`

```sql
CREATE TABLE workspaces (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id          UUID        NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    name             TEXT        NOT NULL,
    officeclaw_token TEXT        UNIQUE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### `officeclaw_token` removed from `"user"`

The field moves entirely to `workspaces`. The `"user"` table reverts to a pure better-auth table with no app-domain fields.

### All app tables: `user_id` → `workspace_id`

| Old name | New name | FK change |
|---|---|---|
| `agents` | `agents` | `user_id → "user"` becomes `workspace_id → workspaces` |
| `skills` | `skills` | same |
| `user_envs` | `workspace_envs` | same |
| `user_channels` | `workspace_channels` | same |
| `user_mcp` | `workspace_mcp` | same |
| `user_templates` | `workspace_templates` | same |

Unique constraints updated accordingly: `UNIQUE(user_id, name)` → `UNIQUE(workspace_id, name)`.

### Migration strategy

No existing users. Rewrite `api/migrations/versions/001_initial_schema.sql` in place. No data migration needed.

---

## 2. Python API

### New domain: `workspace`

Full hexagonal structure at `api/src/workspace/`:

```
workspace/
  core/
    schema.py            # WorkspaceCreate, WorkspaceOut
    ports/
      inbound.py         # IWorkspaceApp
      outbound.py        # IWorkspaceRepo
  app/
    __init__.py          # WorkspaceApp facade
    workspaces.py        # WorkspaceService
  adapters/
    _in/router.py        # POST /workspaces, GET /workspaces
    out/repository.py    # asyncpg impl
  di.py                  # wires repo → service → app
```

### Bootstrap moves to `WorkspaceService`

`_bootstrap_admin` leaves `UserService` → becomes `WorkspaceService._bootstrap(workspace_id)`. Logic is identical, but `workspace_id` replaces `user_id` in all resource creation calls.

Bootstrap creates:
1. `officeclaw_token` → stored on the workspace row
2. `officeclaw` env (`OFFICECLAW_TOKEN`) → scoped to `workspace_id`
3. `default-llm` env → scoped to `workspace_id`
4. Admin agent → scoped to `workspace_id`
5. `SOUL.md`, `AGENTS.md`, `TOOLS.md` agent files
6. `officeclaw-admin` MCP config → scoped to `workspace_id`
7. Attach MCP + envs to Admin agent

### Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/users/{user_id}/bootstrap` | Called by SvelteKit after better-auth user creation. Delegates to `workspace_app.create_workspace(user_id, name="Personal")`. |
| `POST` | `/workspaces` | Create new workspace + run bootstrap. Body: `{user_id, name}`. Returns workspace with token. |
| `GET` | `/workspaces?user_id={id}` | List all workspaces for a user. |

### MCP auth

Old: `find_by_token(token)` queries `"user"` → returns `user_id`.  
New: `find_by_token(token)` queries `workspaces` → returns `{workspace_id, user_id}`.

MCP router scopes all fleet operations to `workspace_id`.

### All fleet / integrations / knowledge services

Every method signature that accepts `user_id: UUID` for resource scoping changes to `workspace_id: UUID`. Business logic is unchanged.

### Wiring order in `main.py` lifespan

```
integrations → library → fleet → workspace → identity → knowledge
```

`workspace` comes after `fleet` and `integrations` (bootstrap depends on both).  
`identity` comes after `workspace` (bootstrap now delegates into `WorkspaceApp`).

---

## 3. Web (SvelteKit + Drizzle)

### Drizzle schema changes

**`web/src/lib/server/db/app.schema.ts`**
- Add `workspaces` table
- Rename table objects: `userEnvs` → `workspaceEnvs`, `userChannels` → `workspaceChannels`, `userMcp` → `workspaceMcp`, `userTemplates` → `workspaceTemplates`
- Replace `userId` FK → `workspaceId` on all app tables

**`web/src/lib/server/db/auth.schema.ts`**
- Remove `officeclawToken` field from `user` table definition

### URL structure

Workspace context is explicit in the URL:

```
/w/[workspaceId]/agents
/w/[workspaceId]/skills
/w/[workspaceId]/envs
/w/[workspaceId]/channels
...
```

Root `/` and `/dashboard` redirect to the user's first (default) workspace.

### Load functions

```
session → user_id → workspaces[] → active workspace_id (from URL param)
```

The `[workspaceId]` param is validated in the layout load: must belong to the current user. Unauthorized → 403.

### Server actions

All actions that previously sent `user_id` to the Python API now send `workspace_id` extracted from the URL param.

### UI: workspace switcher

- Location: bottom of sidebar
- Shows: current workspace name + avatar/initial
- Click → popover/dropdown with:
  - List of user's workspaces (name, clickable → navigate to `/w/[id]/...`)
  - "New workspace" button → modal with name input → `POST /workspaces` → redirect to new workspace
- Active workspace is highlighted

---

## 4. What does NOT change

- better-auth tables (`session`, `account`, `verification`) — untouched
- `agent_files`, `agent_skills`, `agent_envs`, `agent_channels`, `agent_mcp`, `agent_user_templates` — these already FK to `agents`, no change needed
- Bootstrap logic (content of `SOUL.md`, `AGENTS.md`, etc.) — identical, just scoped to workspace

---

## 5. Open questions (deferred)

- Workspace deletion: cascade-deletes all resources including running sandbox containers — needs careful orchestration with `msb` CLI. Deferred.
- Workspace rename: straightforward PATCH, deferred to implementation.
- Per-workspace `is_default` flag: deferred — for now, "Personal" workspace created first is the default by convention (oldest `created_at`).
