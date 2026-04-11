# User Templates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a typed prompt-template library (`user_templates`) that users own and selectively attach to agents (max 1 per type per agent), with template content prepended to the corresponding runtime file when the sandbox starts.

**Architecture:** `user_templates` is a first-class workspace entity (like skills/envs) — users build a library, attach one template per type to each agent. At sandbox start `vm_payload.py` merges: `template_content + "\n---\n" + agent_file_content` for each of the 5 runtime file types (`user`, `soul`, `agents`, `heartbeat`, `tools`). The junction table `agent_user_templates` denormalises `template_type` to enforce the uniqueness constraint at the DB level.

**Tech Stack:** PostgreSQL (raw SQL migration), asyncpg, Python/FastAPI (hexagonal), Drizzle ORM (Drizzle schema only — no migrations), SvelteKit

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `api/migrations/versions/004_user_templates.sql` | Create | DB tables + constraint |
| `web/src/lib/server/db/app.schema.ts` | Modify | Drizzle types for new tables |
| `api/src/integrations/adapters/out/repository.py` | Modify | `UserTemplateRepo` + `LinkRepo` template methods |
| `api/src/integrations/app/service.py` | Modify | Template CRUD + attach/detach/list facade methods |
| `api/src/integrations/di.py` | Modify | Wire `UserTemplateRepo` |
| `api/src/fleet/app/vm_payload.py` | Modify | Merge logic at sandbox start |
| `api/src/entrypoint/mcp.py` | Modify | Improve `update_agent_file` docstring |

---

## Task 1: SQL Migration

**Files:**
- Create: `api/migrations/versions/004_user_templates.sql`

- [ ] **Step 1: Write the migration**

```sql
-- ============================================================
-- User prompt-template library + agent attachment junction
-- ============================================================

CREATE TABLE user_templates (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID        NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    name          TEXT        NOT NULL,
    template_type TEXT        NOT NULL CHECK (template_type IN ('user','soul','agents','heartbeat','tools')),
    content       TEXT        NOT NULL DEFAULT '',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- One template per type per agent (enforced via denormalised template_type column)
CREATE TABLE agent_user_templates (
    agent_id          UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    user_template_id  UUID NOT NULL REFERENCES user_templates(id) ON DELETE CASCADE,
    template_type     TEXT NOT NULL CHECK (template_type IN ('user','soul','agents','heartbeat','tools')),
    PRIMARY KEY (agent_id, user_template_id),
    UNIQUE (agent_id, template_type)
);
```

- [ ] **Step 2: Apply the migration**

```bash
cd /Users/vladimirbeliaev/vvbeliaev/officeclaw
# Apply via psql against your local DB (adjust DATABASE_URL as needed)
psql "$DATABASE_URL" -f api/migrations/versions/004_user_templates.sql
```

Expected: no errors, two new tables visible in `\dt`.

- [ ] **Step 3: Commit**

```bash
git add api/migrations/versions/004_user_templates.sql
git commit -m "feat(db): add user_templates library and agent_user_templates junction"
```

---

## Task 2: Drizzle Schema

**Files:**
- Modify: `web/src/lib/server/db/app.schema.ts`

- [ ] **Step 1: Add `userTemplates` table definition**

After the `userMcp` table block (around line 115), add:

```typescript
export const userTemplates = pgTable('user_templates', {
	id: uuid().defaultRandom().primaryKey().notNull(),
	userId: uuid('user_id')
		.notNull()
		.references(() => user.id, { onDelete: 'cascade' }),
	name: text().notNull(),
	templateType: text('template_type').notNull(), // 'user'|'soul'|'agents'|'heartbeat'|'tools'
	content: text().default('').notNull(),
	createdAt: timestamp('created_at', { withTimezone: true }).defaultNow().notNull(),
	updatedAt: timestamp('updated_at', { withTimezone: true }).defaultNow().notNull()
});

export const agentUserTemplates = pgTable(
	'agent_user_templates',
	{
		agentId: uuid('agent_id')
			.notNull()
			.references(() => agents.id, { onDelete: 'cascade' }),
		userTemplateId: uuid('user_template_id')
			.notNull()
			.references(() => userTemplates.id, { onDelete: 'cascade' }),
		templateType: text('template_type').notNull()
	},
	(t) => [
		primaryKey({ columns: [t.agentId, t.userTemplateId] }),
		unique('agent_user_templates_agent_id_template_type_key').on(t.agentId, t.templateType)
	]
);
```

- [ ] **Step 2: Add relations**

At the end of the relations block, add:

```typescript
export const userTemplatesRelations = relations(userTemplates, ({ one, many }) => ({
	user: one(user, { fields: [userTemplates.userId], references: [user.id] }),
	agents: many(agentUserTemplates)
}));

export const agentUserTemplatesRelations = relations(agentUserTemplates, ({ one }) => ({
	agent: one(agents, { fields: [agentUserTemplates.agentId], references: [agents.id] }),
	template: one(userTemplates, {
		fields: [agentUserTemplates.userTemplateId],
		references: [userTemplates.id]
	})
}));
```

Also extend `agentsRelations` to include `templates: many(agentUserTemplates)`.

- [ ] **Step 3: Commit**

```bash
git add web/src/lib/server/db/app.schema.ts
git commit -m "feat(drizzle): add userTemplates and agentUserTemplates schema"
```

---

## Task 3: Repository Layer

**Files:**
- Modify: `api/src/integrations/adapters/out/repository.py`

- [ ] **Step 1: Add `UserTemplateRepo` class**

After `UserMcpRepo` class, add:

```python
class UserTemplateRepo:
    def __init__(self, conn: asyncpg.Pool) -> None:
        self._conn = conn

    async def create(
        self, user_id: UUID, name: str, template_type: str, content: str
    ) -> asyncpg.Record:
        return await self._conn.fetchrow(
            "INSERT INTO user_templates (user_id, name, template_type, content)"
            " VALUES ($1, $2, $3, $4)"
            " RETURNING id, user_id, name, template_type, content, created_at, updated_at",
            user_id, name, template_type, content,
        )

    async def find_by_id(self, template_id: UUID) -> asyncpg.Record | None:
        return await self._conn.fetchrow(
            "SELECT id, user_id, name, template_type, content, created_at, updated_at"
            " FROM user_templates WHERE id = $1",
            template_id,
        )

    async def list_by_user(self, user_id: UUID) -> list[asyncpg.Record]:
        return await self._conn.fetch(
            "SELECT id, user_id, name, template_type, content, created_at, updated_at"
            " FROM user_templates WHERE user_id = $1 ORDER BY created_at DESC",
            user_id,
        )

    async def update(
        self, template_id: UUID, name: str | None = None, content: str | None = None
    ) -> asyncpg.Record | None:
        parts: list[str] = ["updated_at = now()"]
        params: list = [template_id]
        i = 2
        if name is not None:
            parts.append(f"name = ${i}")
            params.append(name)
            i += 1
        if content is not None:
            parts.append(f"content = ${i}")
            params.append(content)
            i += 1
        return await self._conn.fetchrow(
            f"UPDATE user_templates SET {', '.join(parts)} WHERE id = $1"
            " RETURNING id, user_id, name, template_type, content, created_at, updated_at",
            *params,
        )

    async def delete(self, template_id: UUID) -> None:
        await self._conn.execute("DELETE FROM user_templates WHERE id = $1", template_id)
```

- [ ] **Step 2: Extend `LinkRepo` with template methods**

Inside `LinkRepo`, add after `list_mcps_decrypted`:

```python
    async def attach_template(
        self, agent_id: UUID, template_id: UUID, template_type: str
    ) -> None:
        await self._conn.execute(
            "INSERT INTO agent_user_templates (agent_id, user_template_id, template_type)"
            " VALUES ($1, $2, $3)"
            " ON CONFLICT ON CONSTRAINT agent_user_templates_agent_id_template_type_key"
            " DO UPDATE SET user_template_id = EXCLUDED.user_template_id",
            agent_id, template_id, template_type,
        )

    async def detach_template(self, agent_id: UUID, template_id: UUID) -> None:
        await self._conn.execute(
            "DELETE FROM agent_user_templates"
            " WHERE agent_id = $1 AND user_template_id = $2",
            agent_id, template_id,
        )

    async def list_templates(self, agent_id: UUID) -> list[asyncpg.Record]:
        return await self._conn.fetch(
            "SELECT t.id, t.user_id, t.name, t.template_type, t.content, t.created_at"
            " FROM user_templates t"
            " JOIN agent_user_templates a ON a.user_template_id = t.id"
            " WHERE a.agent_id = $1",
            agent_id,
        )
```

Note: `attach_template` uses `DO UPDATE SET` (upsert) so that attaching a new template of the same type automatically replaces the old one — matches the "1 per type" contract without the caller needing to detach first.

- [ ] **Step 3: Commit**

```bash
git add api/src/integrations/adapters/out/repository.py
git commit -m "feat(integrations): add UserTemplateRepo and LinkRepo template methods"
```

---

## Task 4: Service & DI

**Files:**
- Modify: `api/src/integrations/app/service.py`
- Modify: `api/src/integrations/di.py`

- [ ] **Step 1: Update `IntegrationsService.__init__` signature**

Add `template_repo` parameter:

```python
from src.integrations.adapters.out.repository import (
    ChannelRepo,
    EnvRepo,
    LinkRepo,
    UserMcpRepo,
    UserTemplateRepo,
)

class IntegrationsService:
    def __init__(
        self,
        env_repo: EnvRepo,
        channel_repo: ChannelRepo,
        link_repo: LinkRepo,
        mcp_repo: UserMcpRepo,
        template_repo: UserTemplateRepo,
    ) -> None:
        self._envs = env_repo
        self._channels = channel_repo
        self._links = link_repo
        self._mcp = mcp_repo
        self._templates = template_repo
```

- [ ] **Step 2: Add template facade methods**

At the end of `IntegrationsService`, add:

```python
    # --- Templates ---

    async def create_template(
        self, user_id: UUID, name: str, template_type: str, content: str
    ) -> asyncpg.Record:
        return await self._templates.create(user_id, name, template_type, content)

    async def find_template(self, template_id: UUID) -> asyncpg.Record | None:
        return await self._templates.find_by_id(template_id)

    async def list_templates(self, user_id: UUID) -> list[asyncpg.Record]:
        return await self._templates.list_by_user(user_id)

    async def update_template(
        self, template_id: UUID, name: str | None = None, content: str | None = None
    ) -> asyncpg.Record | None:
        return await self._templates.update(template_id, name=name, content=content)

    async def delete_template(self, template_id: UUID) -> None:
        await self._templates.delete(template_id)

    # --- Links: templates ---

    async def attach_template(
        self, agent_id: UUID, template_id: UUID, template_type: str
    ) -> None:
        await self._links.attach_template(agent_id, template_id, template_type)

    async def detach_template(self, agent_id: UUID, template_id: UUID) -> None:
        await self._links.detach_template(agent_id, template_id)

    async def list_agent_templates(self, agent_id: UUID) -> list[asyncpg.Record]:
        return await self._links.list_templates(agent_id)
```

- [ ] **Step 3: Update `di.py`**

```python
from src.integrations.adapters.out.repository import (
    ChannelRepo,
    EnvRepo,
    LinkRepo,
    UserMcpRepo,
    UserTemplateRepo,
)
from src.integrations.app import IntegrationsApp


def build(pool: asyncpg.Pool) -> IntegrationsApp:
    return IntegrationsApp(
        env_repo=EnvRepo(pool),
        channel_repo=ChannelRepo(pool),
        link_repo=LinkRepo(pool),
        mcp_repo=UserMcpRepo(pool),
        template_repo=UserTemplateRepo(pool),
    )
```

- [ ] **Step 4: Commit**

```bash
git add api/src/integrations/app/service.py api/src/integrations/di.py
git commit -m "feat(integrations): wire UserTemplateRepo into IntegrationsService"
```

---

## Task 5: vm_payload Merge Logic

**Files:**
- Modify: `api/src/fleet/app/vm_payload.py`

Context: `build_vm_payload` currently iterates `list_files` and appends everything. We need to split runtime files from regular files and merge runtime ones with attached templates.

- [ ] **Step 1: Add the type→path mapping constant**

At the top of the file, after imports, add:

```python
# Maps template_type to the nanobot runtime filename it controls.
_RUNTIME_FILES: dict[str, str] = {
    "user":      "USER.md",
    "soul":      "SOUL.md",
    "agents":    "AGENTS.md",
    "heartbeat": "HEARTBEAT.md",
    "tools":     "TOOLS.md",
}
```

- [ ] **Step 2: Replace the file-assembly block in `build_vm_payload`**

Current code (lines 37–48):
```python
    # 1. Agent workspace files
    files: list[dict] = []
    for rec in await agents.list_files(agent_id):
        files.append({"path": rec["path"], "content": rec["content"]})
```

Replace with:

```python
    # 1. Agent workspace files — split runtime files from regular files
    files: list[dict] = []
    agent_runtime: dict[str, str] = {}  # path → content for runtime files
    runtime_paths = set(_RUNTIME_FILES.values())

    for rec in await agents.list_files(agent_id):
        if rec["path"] in runtime_paths:
            agent_runtime[rec["path"]] = rec["content"]
        else:
            files.append({"path": rec["path"], "content": rec["content"]})

    # 1b. Attached templates → merge (prepend) with agent runtime files
    attached_templates = await integrations.list_agent_templates(agent_id)
    template_by_type: dict[str, str] = {
        t["template_type"]: t["content"] for t in attached_templates
    }

    for ttype, path in _RUNTIME_FILES.items():
        tpl = template_by_type.get(ttype)
        override = agent_runtime.get(path)
        if tpl and override:
            content = tpl + "\n---\n" + override
        elif tpl:
            content = tpl
        elif override:
            content = override
        else:
            continue
        files.append({"path": path, "content": content})
```

- [ ] **Step 3: Verify the rest of `build_vm_payload` is unchanged**

The skill-files block (step 2), env-vars block (step 3), and config block (step 4) are untouched.

- [ ] **Step 4: Commit**

```bash
git add api/src/fleet/app/vm_payload.py
git commit -m "feat(vm_payload): merge user_templates into runtime files at sandbox start"
```

---

## Task 6: MCP Docstring

**Files:**
- Modify: `api/src/entrypoint/mcp.py`

- [ ] **Step 1: Update `update_agent_file` docstring**

Replace the current docstring:

```python
    """Upsert a workspace file for an agent."""
```

With:

```python
    """Upsert a workspace file for an agent.

    Special runtime files (exact paths, recognised by nanobot):
      SOUL.md       — agent identity, personality, persistent goals
      AGENTS.md     — sub-agents this agent can spawn and delegate to
      HEARTBEAT.md  — scheduled / recurring tasks the agent runs autonomously
      TOOLS.md      — tool configuration and usage guidance
      USER.md       — description of the agent's owner (who they are, context)

    If the user has attached a template of the matching type to this agent,
    that template content is prepended automatically when the sandbox starts —
    write only the agent-specific additions here, not the shared base.

    For non-runtime files pass any relative path (e.g. 'notes/ideas.md').
    """
```

- [ ] **Step 2: Commit**

```bash
git add api/src/entrypoint/mcp.py
git commit -m "docs(mcp): document runtime file paths in update_agent_file tool"
```

---

## Self-Review

**Spec coverage:**
- ✅ `user_templates` library table — Task 1
- ✅ `agent_user_templates` junction with 1-per-type constraint — Task 1
- ✅ Drizzle schema mirrors SQL — Task 2
- ✅ Hexagonal repo/service/di — Tasks 3-4
- ✅ Merge (prepend) in `vm_payload.py` — Task 5
- ✅ `update_agent_file` docstring for Admin agent — Task 6
- ✅ `user` type included in both CHECK constraint and `_RUNTIME_FILES` map

**Type consistency:**
- `template_type` string passed through all layers — repo, service, link, vm_payload — consistent
- `attach_template` takes `template_type` explicitly from caller (service layer already knows it from `find_template`)
- `_RUNTIME_FILES` is the single source of truth for type→path mapping
