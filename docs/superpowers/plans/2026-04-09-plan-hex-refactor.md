# Hexagonal Architecture Refactoring

**Goal:** Reorganise `api/src/` from a technical-type layout (`models/`, `repositories/`, `routers/`) to a domain-driven hexagonal layout with 4 domain hexes + 1 ports layer.

**Strategy:** Create new files alongside old ones (steps 1–5 add only). Step 6 switches entry points and deletes old code. Tests run only after step 6. Each step is a clean commit.

## Target layout

```
src/
  shared/
    config.py          ← src/config.py
    crypto.py          ← src/crypto.py
    db/                ← src/db/
  identity/
    schema.py          ← models/user.py
    repository.py      ← repositories/users.py
    service.py         ← admin.py  (bootstrap logic)
    router.py          ← routers/users.py
  library/
    schema.py          ← models/skill.py
    repository.py      ← repositories/skills.py
    router.py          ← routers/skills.py
  fleet/
    schema.py          ← models/agent.py + models/agent_file.py
    repository.py      ← repositories/agents.py + repositories/agent_files.py
    router.py          ← routers/agents.py
  integrations/
    schema.py          ← models/env.py + models/channel.py + models/mcp.py
    repository.py      ← repositories/envs.py + repositories/channels.py
                          + repositories/links.py + repositories/mcp.py
    router.py          ← routers/envs.py + routers/channels.py + routers/links.py
  ports/
    rest/
      main.py          ← main.py
    mcp/
      server.py        ← mcp_server.py
    sandbox/
      vm_payload.py    ← vm_payload.py
```

## Import map (new paths)

```python
from src.shared.config import get_settings
from src.shared.crypto import encrypt_json, decrypt_json
from src.shared.db.pool import get_pool, create_pool, close_pool

from src.identity.schema import UserCreate, UserOut, UserRegistered
from src.identity.repository import UserRepo
from src.identity.service import create_admin_for_user

from src.library.schema import SkillCreate, SkillOut, SkillFileIn, SkillFileOut
from src.library.repository import SkillRepo, SkillFileRepo

from src.fleet.schema import AgentCreate, AgentOut, AgentUpdate, AgentStatus, AgentFileIn, AgentFileOut
from src.fleet.repository import AgentRepo, AgentFileRepo

from src.integrations.schema import EnvCreate, EnvOut, ChannelCreate, ChannelOut, McpCreate, McpOut
from src.integrations.repository import EnvRepo, ChannelRepo, LinkRepo, AgentMcpRepo

from src.ports.mcp.server import mcp, set_pool
```

---

## Task 1: Create shared/ and directory skeleton

**Files to create:**
- `src/shared/__init__.py` (empty)
- `src/shared/config.py` — copy of `src/config.py` (no import changes needed)
- `src/shared/crypto.py` — copy of `src/crypto.py` (no import changes needed)
- `src/shared/db/__init__.py` (empty)
- `src/shared/db/pool.py` — copy of `src/db/pool.py` (no import changes needed)
- `src/identity/__init__.py`, `src/library/__init__.py`, `src/fleet/__init__.py`
- `src/integrations/__init__.py`
- `src/ports/__init__.py`, `src/ports/rest/__init__.py`, `src/ports/mcp/__init__.py`, `src/ports/sandbox/__init__.py`

Old files stay untouched. No tests yet.

Commit: `refactor(api): hex skeleton — shared/ layer + empty domain __init__.py`

---

## Task 2: identity/

**Files to create:**

`src/identity/__init__.py` — already created in Task 1

`src/identity/schema.py`:
```python
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr


class UserOut(BaseModel):
    id: UUID
    email: str
    created_at: datetime


class UserRegistered(BaseModel):
    id: UUID
    email: str
    created_at: datetime
    officeclaw_token: str  # shown once at registration, store it securely
```

`src/identity/repository.py`:
```python
from uuid import UUID
import asyncpg


class UserRepo:
    def __init__(self, conn: asyncpg.Connection) -> None:
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

`src/identity/service.py` — content of `src/admin.py` with updated imports:
- `from src.shared.config import get_settings`
- `from src.fleet.repository import AgentRepo, AgentFileRepo`
- `from src.integrations.repository import EnvRepo, LinkRepo, AgentMcpRepo`
- `from src.identity.repository import UserRepo`

`src/identity/router.py` — content of `src/routers/users.py` with updated imports:
- `from src.identity.service import create_admin_for_user`
- `from src.shared.db.pool import get_pool`
- `from src.identity.schema import UserCreate, UserOut, UserRegistered`
- `from src.identity.repository import UserRepo`

Commit: `refactor(api): hex identity/ — schema, repository, service, router`

---

## Task 3: library/

`src/library/schema.py` — content of `src/models/skill.py` (no import changes)

`src/library/repository.py` — content of `src/repositories/skills.py` (no import changes — only uses asyncpg)

`src/library/router.py` — content of `src/routers/skills.py` with updated imports:
- `from src.shared.db.pool import get_pool`
- `from src.library.schema import SkillCreate, SkillOut, SkillFileIn, SkillFileOut`
- `from src.library.repository import SkillRepo, SkillFileRepo`

Commit: `refactor(api): hex library/ — schema, repository, router`

---

## Task 4: fleet/

`src/fleet/schema.py` — merge of `src/models/agent.py` + `src/models/agent_file.py`:
```python
from datetime import datetime
from uuid import UUID
from typing import Literal
from pydantic import BaseModel

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

`src/fleet/repository.py` — merge of `src/repositories/agents.py` + `src/repositories/agent_files.py` (no import changes — only uses asyncpg)

`src/fleet/router.py` — content of `src/routers/agents.py` with updated imports:
- `from src.shared.db.pool import get_pool`
- `from src.fleet.schema import AgentCreate, AgentOut, AgentUpdate, AgentFileIn, AgentFileOut`
- `from src.fleet.repository import AgentRepo, AgentFileRepo`

Commit: `refactor(api): hex fleet/ — schema, repository, router`

---

## Task 5: integrations/

`src/integrations/schema.py` — merge of `src/models/env.py` + `src/models/channel.py` + `src/models/mcp.py`:
```python
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class EnvCreate(BaseModel):
    user_id: UUID
    name: str
    values: dict


class EnvOut(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    created_at: datetime


class ChannelCreate(BaseModel):
    user_id: UUID
    type: str
    config: dict


class ChannelOut(BaseModel):
    id: UUID
    user_id: UUID
    type: str
    created_at: datetime


class McpCreate(BaseModel):
    name: str
    config: dict


class McpOut(BaseModel):
    id: UUID
    agent_id: UUID
    name: str
```

`src/integrations/repository.py` — merge of `src/repositories/envs.py` + `src/repositories/channels.py` + `src/repositories/links.py` + `src/repositories/mcp.py` with updated imports:
- `from src.shared.crypto import encrypt_json, decrypt_json`

`src/integrations/router.py` — merge of `src/routers/envs.py` + `src/routers/channels.py` + `src/routers/links.py` with updated imports:
- `from src.shared.db.pool import get_pool`
- `from src.integrations.schema import EnvCreate, EnvOut, ChannelCreate, ChannelOut, McpCreate, McpOut`
- `from src.integrations.repository import EnvRepo, ChannelRepo, LinkRepo, AgentMcpRepo`
- `from src.library.schema import SkillOut`  (links router returns SkillOut for /agents/{id}/skills)

Commit: `refactor(api): hex integrations/ — schema, repository, router`

---

## Task 6: ports/ + switch-over + delete old code + tests

### 6.1 Create ports/

`src/ports/rest/main.py` — content of `src/main.py` with updated imports:
```python
from src.shared.db.pool import create_pool, close_pool
from src.ports.mcp.server import mcp, set_pool
from src.identity import router as identity_router
from src.library import router as library_router
from src.fleet import router as fleet_router
from src.integrations import router as integrations_router
```

Wait — routers are in domain modules now, so import from domain:
```python
from src.identity.router import router as users_router
from src.library.router import router as skills_router
from src.fleet.router import router as agents_router
from src.integrations.router import router as envs_router, channels_router, links_router
```

Note: `integrations/router.py` contains envs, channels, and links routers. They can be three separate `router` objects or combined. Use three separate `APIRouter()` instances in `integrations/router.py`: `envs_router`, `channels_router`, `links_router`.

`src/ports/mcp/server.py` — content of `src/mcp_server.py` with updated imports:
- `from src.fleet.repository import AgentRepo, AgentFileRepo`
- `from src.integrations.repository import EnvRepo, ChannelRepo, LinkRepo, AgentMcpRepo`
- `from src.library.repository import SkillRepo`
- `from src.identity.repository import UserRepo`

`src/ports/sandbox/vm_payload.py` — content of `src/vm_payload.py` with updated imports:
- `from src.fleet.repository import AgentFileRepo`
- `from src.integrations.repository import LinkRepo, EnvRepo, ChannelRepo, AgentMcpRepo`
- `from src.library.repository import SkillFileRepo`

### 6.2 Update entry point

`api/src/main.py` becomes a one-liner re-export for backwards compat with gunicorn/uvicorn:
```python
from src.ports.rest.main import app  # noqa: F401
```

Or alternatively: update `pyproject.toml` / uvicorn command to point to `src.ports.rest.main:app`.

Check `pyproject.toml` to see if there's an explicit app entry. If yes, update it. If uvicorn uses `src.main:app`, update to `src.ports.rest.main:app`.

### 6.3 Update conftest.py

`api/tests/conftest.py` imports `from src.main import app` or uses it via `AsyncClient`. Verify and update if needed.

### 6.4 Delete old code

Remove entire old structure:
```
src/models/
src/repositories/
src/routers/
src/admin.py
src/mcp_server.py
src/vm_payload.py
src/config.py
src/crypto.py
src/db/
```

And `src/main.py` if replaced by re-export (or keep as re-export).

### 6.5 Run tests

```bash
cd /Users/vladimirbeliaev/vvbeliaev/officeclaw/api && .venv/bin/python -m pytest -v
```

Expected: 44 passed.

### 6.6 Commit

```
refactor(api): hex ports/ — rest, mcp, sandbox; switch entry points; delete old structure
```

---

## Self-review

### Cross-domain dependency rules

- `identity/service.py` uses `fleet.repository` + `integrations.repository` → OK (service coordinates domains)
- `integrations/router.py` uses `library.schema.SkillOut` → OK (schema is a value object, not infrastructure)
- `ports/` use all domains → OK (ports are the outermost layer)
- NO domain imports from `ports/` → this is the key rule

### What does NOT change

- All SQL queries — verbatim
- All Pydantic models — verbatim
- All test files — only conftest.py may need import update
- All migrations
- Business logic in mcp_server.py (business logic functions)
