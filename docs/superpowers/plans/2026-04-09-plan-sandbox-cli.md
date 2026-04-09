# Sandbox CLI Integration (microsandbox msb)

**Goal:** Wire `POST /agents/{id}/start` and `POST /agents/{id}/stop` to actually launch/stop microVM sandboxes via `msb` CLI.

**Architecture:** `fleet/service.py` owns agent lifecycle. It builds the payload (already done in `adapters/sandbox/vm_payload.py`), writes workspace files to disk, then calls `msb` via asyncio subprocess. MCP tools delegate to the same service functions.

**Security note:** All subprocess calls use `asyncio.create_subprocess_exec(*list, ...)` — never `shell=True`. Arguments are passed as a list, not a shell string. `agent_id` is a validated UUID (safe to interpolate). Env keys/values come from the DB.

**Dependency flow:**
```
fleet/router.py          ──┐
adapters/mcp/server.py   ──┤──► fleet/service.py ──► adapters/sandbox/vm_payload.py
                            │         │
                            │         └──► msb CLI (asyncio.create_subprocess_exec)
                            └──► fleet/repository.py (DB update)
```

---

## Task 1: fleet/service.py — sandbox lifecycle functions

### Files
- Modify: `api/src/fleet/service.py`
- Create: `api/tests/test_sandbox.py`

### Step 1.1: Write failing tests first

Create `api/tests/test_sandbox.py`:

```python
# api/tests/test_sandbox.py
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID
import pytest


@pytest.fixture
async def plain_agent(conn) -> UUID:
    """Create a plain (non-admin) agent with a real user."""
    import uuid
    from src.fleet.repository import AgentRepo
    uid = (await conn.fetchrow(
        "INSERT INTO users (email) VALUES ($1) RETURNING id",
        f"sandbox-test-{uuid.uuid4()}@example.com",
    ))["id"]
    agent = await AgentRepo(conn).create(uid, "TestBot", "ghcr.io/hkuds/nanobot:latest", False)
    return agent["id"]


def _proc(returncode: int = 0, stderr: bytes = b"") -> AsyncMock:
    p = AsyncMock()
    p.returncode = returncode
    p.communicate = AsyncMock(return_value=(b"", stderr))
    return p


async def test_start_sandbox_calls_msb(conn, plain_agent):
    from src.fleet.service import start_agent_sandbox
    with patch("src.fleet.service.asyncio.create_subprocess_exec", return_value=_proc()) as mock_exec, \
         patch("src.fleet.service.Path.mkdir"), \
         patch("builtins.open", MagicMock()):
        await start_agent_sandbox(conn, plain_agent)
    args = mock_exec.call_args[0]
    assert args[0] == "msb"
    assert "run" in args
    assert "--detach" in args
    assert f"agent-{plain_agent}" in args


async def test_start_sandbox_updates_db(conn, plain_agent):
    from src.fleet.service import start_agent_sandbox
    from src.fleet.repository import AgentRepo
    with patch("src.fleet.service.asyncio.create_subprocess_exec", return_value=_proc()), \
         patch("src.fleet.service.Path.mkdir"), \
         patch("builtins.open", MagicMock()):
        await start_agent_sandbox(conn, plain_agent)
    rec = await AgentRepo(conn).find_by_id(plain_agent)
    assert rec["status"] == "running"
    assert rec["sandbox_id"] == f"agent-{plain_agent}"


async def test_start_sandbox_raises_on_failure(conn, plain_agent):
    from src.fleet.service import start_agent_sandbox
    with patch("src.fleet.service.asyncio.create_subprocess_exec",
               return_value=_proc(returncode=1, stderr=b"boom")), \
         patch("src.fleet.service.Path.mkdir"), \
         patch("builtins.open", MagicMock()):
        with pytest.raises(RuntimeError, match="msb run failed"):
            await start_agent_sandbox(conn, plain_agent)


async def test_stop_sandbox_calls_msb_stop_and_rm(conn, plain_agent):
    from src.fleet.service import start_agent_sandbox, stop_agent_sandbox
    with patch("src.fleet.service.asyncio.create_subprocess_exec", return_value=_proc()), \
         patch("src.fleet.service.Path.mkdir"), \
         patch("builtins.open", MagicMock()):
        await start_agent_sandbox(conn, plain_agent)
    with patch("src.fleet.service.asyncio.create_subprocess_exec", return_value=_proc()) as mock_exec, \
         patch("src.fleet.service.shutil.rmtree"):
        await stop_agent_sandbox(conn, plain_agent)
    all_calls = [c[0] for c in mock_exec.call_args_list]
    assert any("stop" in call for call in all_calls)
    assert any("rm" in call for call in all_calls)


async def test_stop_sandbox_updates_db(conn, plain_agent):
    from src.fleet.service import start_agent_sandbox, stop_agent_sandbox
    from src.fleet.repository import AgentRepo
    with patch("src.fleet.service.asyncio.create_subprocess_exec", return_value=_proc()), \
         patch("src.fleet.service.Path.mkdir"), \
         patch("builtins.open", MagicMock()):
        await start_agent_sandbox(conn, plain_agent)
    with patch("src.fleet.service.asyncio.create_subprocess_exec", return_value=_proc()), \
         patch("src.fleet.service.shutil.rmtree"):
        await stop_agent_sandbox(conn, plain_agent)
    rec = await AgentRepo(conn).find_by_id(plain_agent)
    assert rec["status"] == "idle"
    assert rec["sandbox_id"] is None
```

### Step 1.2: Implement in fleet/service.py

Read `api/src/fleet/service.py` first, then append after `create_admin_for_user`.

Add to imports at top of file:
```python
import asyncio
import shutil
from pathlib import Path
```

Append functions:
```python
_SANDBOX_WORKDIR = Path("/tmp/officeclaw")
_DEFAULT_IMAGE = "ghcr.io/hkuds/nanobot:latest"
_DEFAULT_CPUS = "1"
_DEFAULT_MEMORY = "512M"


async def start_agent_sandbox(conn: asyncpg.Connection, agent_id: UUID) -> str:
    """
    Build VM payload, write workspace files to /tmp/officeclaw/<agent_id>/,
    launch sandbox via `msb run --detach`. Returns sandbox_id (msb sandbox name).

    Uses asyncio.create_subprocess_exec (no shell=True — injection-safe).
    """
    from src.adapters.sandbox.vm_payload import build_vm_payload

    payload = await build_vm_payload(conn, agent_id)

    workdir = _SANDBOX_WORKDIR / str(agent_id)
    workdir.mkdir(parents=True, exist_ok=True)

    for f in payload["files"]:
        dest = workdir / f["path"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(f["content"])

    (workdir / "config.json").write_text(payload["config_json"])

    sandbox_name = f"agent-{agent_id}"
    cmd: list[str] = [
        "msb", "run",
        _DEFAULT_IMAGE,
        "--name", sandbox_name,
        "--detach",
        "--volume", f"{workdir}:/workspace",
        "--cpus", _DEFAULT_CPUS,
        "--memory", _DEFAULT_MEMORY,
    ]
    for key, val in payload["env"].items():
        cmd += ["-e", f"{key}={val}"]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"msb run failed: {stderr.decode()}")

    await AgentRepo(conn).update(agent_id, status="running", sandbox_id=sandbox_name)
    return sandbox_name


async def stop_agent_sandbox(conn: asyncpg.Connection, agent_id: UUID) -> None:
    """
    Stop and remove sandbox via `msb stop` + `msb rm`, clean up workspace files.
    Does not raise on msb errors (sandbox may already be gone).
    """
    record = await AgentRepo(conn).find_by_id(agent_id)
    if not record or not record["sandbox_id"]:
        raise ValueError(f"Agent {agent_id} has no running sandbox")

    sandbox_name = record["sandbox_id"]

    for subcmd in (
        ["msb", "stop", sandbox_name],
        ["msb", "rm",   sandbox_name],
    ):
        proc = await asyncio.create_subprocess_exec(
            *subcmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()

    workdir = _SANDBOX_WORKDIR / str(agent_id)
    if workdir.exists():
        shutil.rmtree(workdir)

    await AgentRepo(conn).update(agent_id, status="idle", sandbox_id=None)
```

### Step 1.3: Run tests

```bash
cd /Users/vladimirbeliaev/vvbeliaev/officeclaw/api && .venv/bin/python -m pytest tests/test_sandbox.py -v
```

Expected: 5 passed.

### Step 1.4: Commit

```bash
cd /Users/vladimirbeliaev/vvbeliaev/officeclaw && \
  git add api/src/fleet/service.py api/tests/test_sandbox.py && \
  git commit -m "feat(fleet): start_agent_sandbox + stop_agent_sandbox via msb CLI"
```

---

## Task 2: REST endpoints + MCP hooks

### Files
- Modify: `api/src/fleet/router.py`
- Modify: `api/src/adapters/mcp/server.py`

### Step 2.1: Add POST /{agent_id}/start and /{agent_id}/stop to fleet/router.py

Read the file first. Add these two endpoints after the `delete_agent` endpoint and before the file repo section:

```python
@router.post("/{agent_id}/start", response_model=AgentOut)
async def start_agent(
    agent_id: UUID,
    conn: asyncpg.Connection = Depends(get_pool),
) -> AgentOut:
    record = await AgentRepo(conn).find_by_id(agent_id)
    if not record:
        raise HTTPException(404, "Agent not found")
    if record["status"] == "running":
        raise HTTPException(409, "Agent is already running")
    from src.fleet.service import start_agent_sandbox
    await start_agent_sandbox(conn, agent_id)
    updated = await AgentRepo(conn).find_by_id(agent_id)
    return AgentOut(**dict(updated))


@router.post("/{agent_id}/stop", response_model=AgentOut)
async def stop_agent(
    agent_id: UUID,
    conn: asyncpg.Connection = Depends(get_pool),
) -> AgentOut:
    record = await AgentRepo(conn).find_by_id(agent_id)
    if not record:
        raise HTTPException(404, "Agent not found")
    if record["status"] != "running":
        raise HTTPException(409, "Agent is not running")
    from src.fleet.service import stop_agent_sandbox
    await stop_agent_sandbox(conn, agent_id)
    updated = await AgentRepo(conn).find_by_id(agent_id)
    return AgentOut(**dict(updated))
```

### Step 2.2: Update mcp_start_agent and mcp_stop_agent in adapters/mcp/server.py

Read the file. Find `mcp_start_agent` and `mcp_stop_agent` functions. Replace their bodies:

Current `mcp_start_agent`:
```python
async def mcp_start_agent(conn: asyncpg.Connection, agent_id: UUID) -> dict:
    record = await AgentRepo(conn).update(agent_id, status="running")
    if not record:
        raise ValueError(f"Agent {agent_id} not found")
    return {"id": str(record["id"]), "status": record["status"]}
```

Replace with:
```python
async def mcp_start_agent(conn: asyncpg.Connection, agent_id: UUID) -> dict:
    from src.fleet.service import start_agent_sandbox
    record = await AgentRepo(conn).find_by_id(agent_id)
    if not record:
        raise ValueError(f"Agent {agent_id} not found")
    await start_agent_sandbox(conn, agent_id)
    updated = await AgentRepo(conn).find_by_id(agent_id)
    return {"id": str(updated["id"]), "status": updated["status"]}
```

Current `mcp_stop_agent`:
```python
async def mcp_stop_agent(conn: asyncpg.Connection, agent_id: UUID) -> dict:
    record = await AgentRepo(conn).update(agent_id, status="idle")
    if not record:
        raise ValueError(f"Agent {agent_id} not found")
    return {"id": str(record["id"]), "status": record["status"]}
```

Replace with:
```python
async def mcp_stop_agent(conn: asyncpg.Connection, agent_id: UUID) -> dict:
    from src.fleet.service import stop_agent_sandbox
    record = await AgentRepo(conn).find_by_id(agent_id)
    if not record:
        raise ValueError(f"Agent {agent_id} not found")
    await stop_agent_sandbox(conn, agent_id)
    updated = await AgentRepo(conn).find_by_id(agent_id)
    return {"id": str(updated["id"]), "status": updated["status"]}
```

### Step 2.3: Run full suite

```bash
cd /Users/vladimirbeliaev/vvbeliaev/officeclaw/api && .venv/bin/python -m pytest -v
```

Expected: all 49 passed (44 existing + 5 new sandbox tests).

Note: the existing `test_mcp_start_stop_agent` in test_mcp_tools.py will now call the real `mcp_start_agent` → `start_agent_sandbox`. That test uses `mcp_conn_user` fixture (real DB conn) but subprocess is NOT mocked there. It will fail with `FileNotFoundError: msb not found` unless we handle the case.

Fix: in `test_mcp_tools.py`, patch subprocess for the start/stop test:

```python
async def test_mcp_start_stop_agent(mcp_conn_user):
    from src.ports.mcp.server import mcp_create_agent, mcp_start_agent, mcp_stop_agent
    from unittest.mock import patch, AsyncMock
    conn, user_id = mcp_conn_user

    def _proc():
        p = AsyncMock()
        p.returncode = 0
        p.communicate = AsyncMock(return_value=(b"", b""))
        return p

    agent = await mcp_create_agent(conn, user_id, "StatusBot", "ghcr.io/hkuds/nanobot:latest")
    agent_id = UUID(agent["id"])

    with patch("src.fleet.service.asyncio.create_subprocess_exec", return_value=_proc()), \
         patch("src.fleet.service.Path.mkdir"), \
         patch("builtins.open", MagicMock()):
        started = await mcp_start_agent(conn, agent_id)
    assert started["status"] == "running"

    with patch("src.fleet.service.asyncio.create_subprocess_exec", return_value=_proc()), \
         patch("src.fleet.service.shutil.rmtree"):
        stopped = await mcp_stop_agent(conn, agent_id)
    assert stopped["status"] == "idle"
```

### Step 2.4: Commit

```bash
cd /Users/vladimirbeliaev/vvbeliaev/officeclaw && \
  git add api/src/fleet/router.py api/src/adapters/mcp/server.py api/tests/test_mcp_tools.py && \
  git commit -m "feat(fleet): POST /agents/{id}/start|stop + MCP hooks call real sandbox"
```
