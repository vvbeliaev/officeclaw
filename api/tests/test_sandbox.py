# api/tests/test_sandbox.py
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

import src.fleet.di as fleet_di
import src.integrations.di as integrations_di
import src.library.di as library_di
from src.fleet.app.sandbox import SandboxService

_FAKE_TOKEN = "tok-test"

_WAIT_GW = "src.fleet.app.sandbox._wait_for_gateway"


@pytest.fixture
def fake_runner() -> MagicMock:
    """In-memory ISandboxRunner — every method is an AsyncMock."""
    runner = MagicMock()
    runner.start = AsyncMock(return_value=None)
    runner.stop = AsyncMock(return_value=None)
    runner.remove = AsyncMock(return_value=None)
    runner.force_remove = AsyncMock(return_value=None)
    runner.is_alive = AsyncMock(return_value=True)
    runner.capture_logs = AsyncMock(return_value="(no output)")
    return runner


@pytest.fixture
async def plain_agent(conn) -> UUID:
    """Create a plain (non-admin) agent with a real user and workspace."""
    from src.fleet.adapters.out.repository import AgentRepo
    uid = (await conn.fetchrow(
        'INSERT INTO "user" (email) VALUES ($1) RETURNING id',
        f"sandbox-test-{uuid.uuid4()}@example.com",
    ))["id"]
    workspace_id = (await conn.fetchrow(
        "INSERT INTO workspaces (user_id, name, slug, officeclaw_token) VALUES ($1, $2, $3, $4) RETURNING id",
        uid, "Personal", f"personal-{uuid.uuid4().hex[:8]}", f"tok-{uuid.uuid4()}",
    ))["id"]
    agent = await AgentRepo(conn).create(workspace_id, "TestBot", "ghcr.io/hkuds/nanobot:latest", False)
    return agent["id"]


@pytest.fixture
def sandbox_svc(conn, fake_runner):
    """Build the fleet facade with a fake runner instead of the real adapter.

    Patches `_build_runner` so DI returns our mock — keeps the rest of the
    wiring untouched, so we exercise real AgentService / repos against the
    test database.
    """
    integrations = integrations_di.build(conn)  # type: ignore[arg-type]
    library = library_di.build(conn)  # type: ignore[arg-type]
    with patch.object(fleet_di, "_build_runner", return_value=fake_runner):
        fleet, _ = fleet_di.build(conn, integrations, library)  # type: ignore[arg-type]
    return fleet


async def test_start_sandbox_calls_runner(sandbox_svc, fake_runner, plain_agent):
    with patch("src.fleet.app.sandbox.Path.mkdir"), \
         patch("src.fleet.app.sandbox.Path.rename"), \
         patch("src.fleet.app.sandbox.Path.exists", return_value=False), \
         patch(_WAIT_GW, new_callable=AsyncMock), \
         patch("builtins.open", MagicMock()):
        await sandbox_svc.start_sandbox(plain_agent, _FAKE_TOKEN, "UTC")
    fake_runner.start.assert_awaited_once()
    kwargs = fake_runner.start.call_args.kwargs
    assert kwargs["name"] == f"agent-{plain_agent}"
    assert isinstance(kwargs["workdir"], Path)
    assert isinstance(kwargs["gateway_port"], int)


async def test_start_sandbox_updates_db(conn, sandbox_svc, fake_runner, plain_agent):
    from src.fleet.adapters.out.repository import AgentRepo
    with patch("src.fleet.app.sandbox.Path.mkdir"), \
         patch("src.fleet.app.sandbox.Path.rename"), \
         patch("src.fleet.app.sandbox.Path.exists", return_value=False), \
         patch(_WAIT_GW, new_callable=AsyncMock), \
         patch("builtins.open", MagicMock()):
        await sandbox_svc.start_sandbox(plain_agent, _FAKE_TOKEN, "UTC")
    rec = await AgentRepo(conn).find_by_id(plain_agent)
    assert rec["status"] == "running"
    assert rec["sandbox_id"] == f"agent-{plain_agent}"


async def test_start_sandbox_raises_on_runner_failure(sandbox_svc, fake_runner, plain_agent):
    fake_runner.start.side_effect = RuntimeError("boom")
    with patch("src.fleet.app.sandbox.Path.mkdir"), \
         patch("src.fleet.app.sandbox.Path.rename"), \
         patch("src.fleet.app.sandbox.Path.exists", return_value=False), \
         patch("builtins.open", MagicMock()):
        with pytest.raises(RuntimeError, match="boom"):
            await sandbox_svc.start_sandbox(plain_agent, _FAKE_TOKEN, "UTC")


async def test_start_sandbox_force_removes_orphan_first(sandbox_svc, fake_runner, plain_agent):
    """`start` always calls `force_remove` to clear orphan sandbox names."""
    with patch("src.fleet.app.sandbox.Path.mkdir"), \
         patch("src.fleet.app.sandbox.Path.rename"), \
         patch("src.fleet.app.sandbox.Path.exists", return_value=False), \
         patch(_WAIT_GW, new_callable=AsyncMock), \
         patch("builtins.open", MagicMock()):
        await sandbox_svc.start_sandbox(plain_agent, _FAKE_TOKEN, "UTC")
    fake_runner.force_remove.assert_awaited_with(f"agent-{plain_agent}")


async def test_start_sandbox_tears_down_when_gateway_never_ready(
    sandbox_svc, fake_runner, plain_agent
):
    with patch("src.fleet.app.sandbox.Path.mkdir"), \
         patch("src.fleet.app.sandbox.Path.rename"), \
         patch("src.fleet.app.sandbox.Path.exists", return_value=False), \
         patch(_WAIT_GW, new_callable=AsyncMock, side_effect=RuntimeError("no gw")), \
         patch("builtins.open", MagicMock()):
        with pytest.raises(RuntimeError, match="no gw"):
            await sandbox_svc.start_sandbox(plain_agent, _FAKE_TOKEN, "UTC")
    # force_remove called twice: pre-start orphan cleanup + post-failure cleanup
    assert fake_runner.force_remove.await_count >= 2


async def test_stop_sandbox_calls_runner_stop_and_remove(sandbox_svc, fake_runner, plain_agent):
    with patch("src.fleet.app.sandbox.Path.mkdir"), \
         patch("src.fleet.app.sandbox.Path.rename"), \
         patch("src.fleet.app.sandbox.Path.exists", return_value=False), \
         patch(_WAIT_GW, new_callable=AsyncMock), \
         patch("builtins.open", MagicMock()):
        await sandbox_svc.start_sandbox(plain_agent, _FAKE_TOKEN, "UTC")
    with patch("src.fleet.app.sandbox.shutil.rmtree"):
        await sandbox_svc.stop_sandbox(plain_agent)
    fake_runner.stop.assert_awaited_with(f"agent-{plain_agent}")
    fake_runner.remove.assert_awaited_with(f"agent-{plain_agent}")


async def test_stop_sandbox_updates_db(conn, sandbox_svc, fake_runner, plain_agent):
    from src.fleet.adapters.out.repository import AgentRepo
    with patch("src.fleet.app.sandbox.Path.mkdir"), \
         patch("src.fleet.app.sandbox.Path.rename"), \
         patch("src.fleet.app.sandbox.Path.exists", return_value=False), \
         patch(_WAIT_GW, new_callable=AsyncMock), \
         patch("builtins.open", MagicMock()):
        await sandbox_svc.start_sandbox(plain_agent, _FAKE_TOKEN, "UTC")
    with patch("src.fleet.app.sandbox.shutil.rmtree"):
        await sandbox_svc.stop_sandbox(plain_agent)
    rec = await AgentRepo(conn).find_by_id(plain_agent)
    assert rec["status"] == "idle"
    assert rec["sandbox_id"] is None


def test_read_workspace_files_splits_runtime_on_marker(tmp_path):
    """Runtime files are split on the boundary marker so only the per-agent
    override is persisted. Non-runtime files pass through unchanged.
    """
    from src.fleet.app.sandbox import _read_workspace_files
    from src.fleet.core.runtime_files import BOUNDARY_MARKER

    (tmp_path / "SOUL.md").write_text(
        f"TEMPLATE BODY\n{BOUNDARY_MARKER}\nagent override", encoding="utf-8"
    )
    (tmp_path / "USER.md").write_text("pure override", encoding="utf-8")
    (tmp_path / "notes.md").write_text("free-form notes", encoding="utf-8")

    out = {rec["path"]: rec["content"] for rec in _read_workspace_files(tmp_path)}

    assert out["SOUL.md"] == "agent override"
    assert out["USER.md"] == "pure override"
    assert out["notes.md"] == "free-form notes"


def test_read_workspace_files_skips_runtime_when_only_template(tmp_path):
    """A runtime file that contains only the template (no override after the
    marker) must not create a DB row — otherwise the user would accumulate
    an empty override record on first stop.
    """
    from src.fleet.app.sandbox import _read_workspace_files
    from src.fleet.core.runtime_files import BOUNDARY_MARKER

    (tmp_path / "SOUL.md").write_text(
        f"TEMPLATE ONLY\n{BOUNDARY_MARKER}\n", encoding="utf-8"
    )

    out = {rec["path"]: rec["content"] for rec in _read_workspace_files(tmp_path)}
    assert "SOUL.md" not in out


async def test_stop_sandbox_syncs_mutable_files(conn, sandbox_svc, fake_runner, plain_agent):
    from src.fleet.adapters.out.repository import AgentFileRepo
    with patch("src.fleet.app.sandbox.Path.mkdir"), \
         patch("src.fleet.app.sandbox.Path.rename"), \
         patch("src.fleet.app.sandbox.Path.exists", return_value=False), \
         patch(_WAIT_GW, new_callable=AsyncMock), \
         patch("builtins.open", MagicMock()):
        await sandbox_svc.start_sandbox(plain_agent, _FAKE_TOKEN, "UTC")

    memory_content = "# Memory\nRemembered something."

    fake_workdir = Path(f"/fake-sandboxes/{plain_agent}")
    fake_memory_path = fake_workdir / "memory" / "MEMORY.md"

    def _rglob(self: Path, pattern: str):  # type: ignore[override]
        return [fake_memory_path]

    def _is_file(self: Path) -> bool:
        return str(self).endswith("MEMORY.md")

    def _relative_to(self: Path, other: Path) -> Path:
        return Path("memory/MEMORY.md")

    with patch("src.fleet.app.sandbox.shutil.rmtree"), \
         patch("src.fleet.app.sandbox.Path.exists", return_value=False), \
         patch("pathlib.Path.rglob", _rglob), \
         patch("pathlib.Path.is_file", _is_file), \
         patch("pathlib.Path.relative_to", _relative_to), \
         patch("pathlib.Path.read_text", return_value=memory_content):
        await sandbox_svc.stop_sandbox(plain_agent)

    rec = await AgentFileRepo(conn).find(plain_agent, "memory/MEMORY.md")
    assert rec is not None
    assert rec["content"] == memory_content


async def test_check_health_marks_dead_sandbox_as_error(
    conn, sandbox_svc, fake_runner, plain_agent
):
    """When the runner reports the sandbox dead, agent is marked error and cleaned up."""
    from src.fleet.adapters.out.repository import AgentRepo

    with patch("src.fleet.app.sandbox.Path.mkdir"), \
         patch("src.fleet.app.sandbox.Path.rename"), \
         patch("src.fleet.app.sandbox.Path.exists", return_value=False), \
         patch(_WAIT_GW, new_callable=AsyncMock), \
         patch("builtins.open", MagicMock()):
        await sandbox_svc.start_sandbox(plain_agent, _FAKE_TOKEN, "UTC")

    fake_runner.is_alive.return_value = False

    svc: SandboxService = sandbox_svc._sandbox  # type: ignore[attr-defined]
    with patch("src.fleet.app.sandbox.shutil.rmtree"):
        await svc.check_health()

    rec = await AgentRepo(conn).find_by_id(plain_agent)
    assert rec["status"] == "error"
    assert rec["sandbox_id"] is None
    fake_runner.force_remove.assert_awaited_with(f"agent-{plain_agent}")
