# api/tests/test_sandbox.py
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

import src.fleet.di as fleet_di
import src.integrations.di as integrations_di
import src.library.di as library_di
from src.shared.config import get_settings

_FAKE_TOKEN = "tok-test"

_WAIT_GW = "src.fleet.app.sandbox._wait_for_gateway"


@pytest.fixture(autouse=True)
def force_msb_runner():
    """Pin the sandbox runner to msb regardless of local .env.

    The assertions in this module check for msb-specific command shape;
    developers running with SANDBOX_RUNNER=docker locally would otherwise
    see spurious failures.
    """
    settings = get_settings()
    original = settings.sandbox_runner
    settings.sandbox_runner = "msb"
    try:
        yield
    finally:
        settings.sandbox_runner = original


@pytest.fixture
async def plain_agent(conn) -> UUID:
    """Create a plain (non-admin) agent with a real user and workspace."""
    from src.fleet.adapters.out.repository import AgentRepo
    uid = (await conn.fetchrow(
        'INSERT INTO "user" (email) VALUES ($1) RETURNING id',
        f"sandbox-test-{uuid.uuid4()}@example.com",
    ))["id"]
    workspace_id = (await conn.fetchrow(
        "INSERT INTO workspaces (user_id, name, officeclaw_token) VALUES ($1, $2, $3) RETURNING id",
        uid, "Personal", f"tok-{uuid.uuid4()}",
    ))["id"]
    agent = await AgentRepo(conn).create(workspace_id, "TestBot", "ghcr.io/hkuds/nanobot:latest", False)
    return agent["id"]


@pytest.fixture
def sandbox_svc(conn):
    integrations = integrations_di.build(conn)  # type: ignore[arg-type]
    library = library_di.build(conn)  # type: ignore[arg-type]
    fleet, _ = fleet_di.build(conn, integrations, library)  # type: ignore[arg-type]
    return fleet


def _proc(returncode: int = 0, stderr: bytes = b"") -> AsyncMock:
    p = AsyncMock()
    p.returncode = returncode
    p.communicate = AsyncMock(return_value=(b"", stderr))
    return p


async def test_start_sandbox_calls_msb(sandbox_svc, plain_agent):
    with patch("src.fleet.app.sandbox.asyncio.create_subprocess_exec", return_value=_proc()) as mock_exec, \
         patch("src.fleet.app.sandbox.Path.mkdir"), \
         patch("src.fleet.app.sandbox.Path.rename"), \
         patch("src.fleet.app.sandbox.Path.exists", return_value=False), \
         patch(_WAIT_GW, new_callable=AsyncMock), \
         patch("builtins.open", MagicMock()):
        await sandbox_svc.start_sandbox(plain_agent, _FAKE_TOKEN, "UTC")
    args = mock_exec.call_args[0]
    assert args[0] == "msb"
    assert "run" in args
    assert "--detach" in args
    assert f"agent-{plain_agent}" in args


async def test_start_sandbox_updates_db(conn, sandbox_svc, plain_agent):
    from src.fleet.adapters.out.repository import AgentRepo
    with patch("src.fleet.app.sandbox.asyncio.create_subprocess_exec", return_value=_proc()), \
         patch("src.fleet.app.sandbox.Path.mkdir"), \
         patch("src.fleet.app.sandbox.Path.rename"), \
         patch("src.fleet.app.sandbox.Path.exists", return_value=False), \
         patch(_WAIT_GW, new_callable=AsyncMock), \
         patch("builtins.open", MagicMock()):
        await sandbox_svc.start_sandbox(plain_agent, _FAKE_TOKEN, "UTC")
    rec = await AgentRepo(conn).find_by_id(plain_agent)
    assert rec["status"] == "running"
    assert rec["sandbox_id"] == f"agent-{plain_agent}"


async def test_start_sandbox_raises_on_failure(sandbox_svc, plain_agent):
    with patch("src.fleet.app.sandbox.asyncio.create_subprocess_exec",
               return_value=_proc(returncode=1, stderr=b"boom")), \
         patch("src.fleet.app.sandbox.Path.mkdir"), \
         patch("src.fleet.app.sandbox.Path.rename"), \
         patch("src.fleet.app.sandbox.Path.exists", return_value=False), \
         patch("builtins.open", MagicMock()):
        with pytest.raises(RuntimeError, match="msb run failed"):
            await sandbox_svc.start_sandbox(plain_agent, _FAKE_TOKEN, "UTC")


async def test_stop_sandbox_calls_msb_stop_and_rm(sandbox_svc, plain_agent):
    with patch("src.fleet.app.sandbox.asyncio.create_subprocess_exec", return_value=_proc()), \
         patch("src.fleet.app.sandbox.Path.mkdir"), \
         patch("src.fleet.app.sandbox.Path.rename"), \
         patch("src.fleet.app.sandbox.Path.exists", return_value=False), \
         patch(_WAIT_GW, new_callable=AsyncMock), \
         patch("builtins.open", MagicMock()):
        await sandbox_svc.start_sandbox(plain_agent, _FAKE_TOKEN, "UTC")
    with patch("src.fleet.app.sandbox.asyncio.create_subprocess_exec", return_value=_proc()) as mock_exec, \
         patch("src.fleet.app.sandbox.shutil.rmtree"):
        await sandbox_svc.stop_sandbox(plain_agent)
    all_calls = [c[0] for c in mock_exec.call_args_list]
    assert any("stop" in call for call in all_calls)
    assert any("rm" in call for call in all_calls)


async def test_stop_sandbox_updates_db(conn, sandbox_svc, plain_agent):
    from src.fleet.adapters.out.repository import AgentRepo
    with patch("src.fleet.app.sandbox.asyncio.create_subprocess_exec", return_value=_proc()), \
         patch("src.fleet.app.sandbox.Path.mkdir"), \
         patch("src.fleet.app.sandbox.Path.rename"), \
         patch("src.fleet.app.sandbox.Path.exists", return_value=False), \
         patch(_WAIT_GW, new_callable=AsyncMock), \
         patch("builtins.open", MagicMock()):
        await sandbox_svc.start_sandbox(plain_agent, _FAKE_TOKEN, "UTC")
    with patch("src.fleet.app.sandbox.asyncio.create_subprocess_exec", return_value=_proc()), \
         patch("src.fleet.app.sandbox.shutil.rmtree"):
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

    # SOUL.md was assembled with template + override
    (tmp_path / "SOUL.md").write_text(
        f"TEMPLATE BODY\n{BOUNDARY_MARKER}\nagent override", encoding="utf-8"
    )
    # USER.md had no template attached (no marker) — full body is override
    (tmp_path / "USER.md").write_text("pure override", encoding="utf-8")
    # A non-runtime file — always copied verbatim
    (tmp_path / "notes.md").write_text("free-form notes", encoding="utf-8")

    out = {rec["path"]: rec["content"] for rec in _read_workspace_files(tmp_path)}

    assert out["SOUL.md"] == "agent override"
    assert out["USER.md"] == "pure override"
    assert out["notes.md"] == "free-form notes"


def test_read_workspace_files_skips_runtime_when_only_template(tmp_path):
    """A runtime file that contains only the template (no override after the
    marker) must not create a DB row — otherwise the user would accumulate
    an empty override record on first stop."""
    from src.fleet.app.sandbox import _read_workspace_files
    from src.fleet.core.runtime_files import BOUNDARY_MARKER

    (tmp_path / "SOUL.md").write_text(
        f"TEMPLATE ONLY\n{BOUNDARY_MARKER}\n", encoding="utf-8"
    )

    out = {rec["path"]: rec["content"] for rec in _read_workspace_files(tmp_path)}
    assert "SOUL.md" not in out


async def test_stop_sandbox_syncs_mutable_files(conn, sandbox_svc, plain_agent):
    from pathlib import Path
    from src.fleet.adapters.out.repository import AgentFileRepo
    with patch("src.fleet.app.sandbox.asyncio.create_subprocess_exec", return_value=_proc()), \
         patch("src.fleet.app.sandbox.Path.mkdir"), \
         patch("src.fleet.app.sandbox.Path.rename"), \
         patch("src.fleet.app.sandbox.Path.exists", return_value=False), \
         patch(_WAIT_GW, new_callable=AsyncMock), \
         patch("builtins.open", MagicMock()):
        await sandbox_svc.start_sandbox(plain_agent, _FAKE_TOKEN, "UTC")

    memory_content = "# Memory\nRemembered something."

    # Build a fake MEMORY.md path that rglob would return
    fake_workdir = Path(f"/fake-sandboxes/{plain_agent}")
    fake_memory_path = fake_workdir / "memory" / "MEMORY.md"

    def _rglob(self: Path, pattern: str):  # type: ignore[override]
        return [fake_memory_path]

    def _is_file(self: Path) -> bool:
        return str(self).endswith("MEMORY.md")

    def _relative_to(self: Path, other: Path) -> Path:
        return Path("memory/MEMORY.md")

    with patch("src.fleet.app.sandbox.asyncio.create_subprocess_exec", return_value=_proc()), \
         patch("src.fleet.app.sandbox.shutil.rmtree"), \
         patch("src.fleet.app.sandbox.Path.exists", return_value=False), \
         patch("pathlib.Path.rglob", _rglob), \
         patch("pathlib.Path.is_file", _is_file), \
         patch("pathlib.Path.relative_to", _relative_to), \
         patch("pathlib.Path.read_text", return_value=memory_content):
        await sandbox_svc.stop_sandbox(plain_agent)

    rec = await AgentFileRepo(conn).find(plain_agent, "memory/MEMORY.md")
    assert rec is not None
    assert rec["content"] == memory_content
