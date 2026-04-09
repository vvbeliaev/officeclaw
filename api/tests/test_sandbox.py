# api/tests/test_sandbox.py
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

import src.fleet.di as fleet_di
import src.integrations.di as integrations_di
import src.library.di as library_di


@pytest.fixture
async def plain_agent(conn) -> UUID:
    """Create a plain (non-admin) agent with a real user."""
    from src.fleet.adapters.out.repository import AgentRepo
    uid = (await conn.fetchrow(
        "INSERT INTO users (email) VALUES ($1) RETURNING id",
        f"sandbox-test-{uuid.uuid4()}@example.com",
    ))["id"]
    agent = await AgentRepo(conn).create(uid, "TestBot", "ghcr.io/hkuds/nanobot:latest", False)
    return agent["id"]


@pytest.fixture
def sandbox_svc(conn):
    integrations = integrations_di.build(conn)  # type: ignore[arg-type]
    library = library_di.build(conn)  # type: ignore[arg-type]
    return fleet_di.build(conn, integrations, library)  # type: ignore[arg-type]


def _proc(returncode: int = 0, stderr: bytes = b"") -> AsyncMock:
    p = AsyncMock()
    p.returncode = returncode
    p.communicate = AsyncMock(return_value=(b"", stderr))
    return p


async def test_start_sandbox_calls_msb(sandbox_svc, plain_agent):
    with patch("src.fleet.app.sandbox.asyncio.create_subprocess_exec", return_value=_proc()) as mock_exec, \
         patch("src.fleet.app.sandbox.Path.mkdir"), \
         patch("builtins.open", MagicMock()):
        await sandbox_svc.start_sandbox(plain_agent)
    args = mock_exec.call_args[0]
    assert args[0] == "msb"
    assert "run" in args
    assert "--detach" in args
    assert f"agent-{plain_agent}" in args


async def test_start_sandbox_updates_db(conn, sandbox_svc, plain_agent):
    from src.fleet.adapters.out.repository import AgentRepo
    with patch("src.fleet.app.sandbox.asyncio.create_subprocess_exec", return_value=_proc()), \
         patch("src.fleet.app.sandbox.Path.mkdir"), \
         patch("builtins.open", MagicMock()):
        await sandbox_svc.start_sandbox(plain_agent)
    rec = await AgentRepo(conn).find_by_id(plain_agent)
    assert rec["status"] == "running"
    assert rec["sandbox_id"] == f"agent-{plain_agent}"


async def test_start_sandbox_raises_on_failure(sandbox_svc, plain_agent):
    with patch("src.fleet.app.sandbox.asyncio.create_subprocess_exec",
               return_value=_proc(returncode=1, stderr=b"boom")), \
         patch("src.fleet.app.sandbox.Path.mkdir"), \
         patch("builtins.open", MagicMock()):
        with pytest.raises(RuntimeError, match="msb run failed"):
            await sandbox_svc.start_sandbox(plain_agent)


async def test_stop_sandbox_calls_msb_stop_and_rm(sandbox_svc, plain_agent):
    with patch("src.fleet.app.sandbox.asyncio.create_subprocess_exec", return_value=_proc()), \
         patch("src.fleet.app.sandbox.Path.mkdir"), \
         patch("builtins.open", MagicMock()):
        await sandbox_svc.start_sandbox(plain_agent)
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
         patch("builtins.open", MagicMock()):
        await sandbox_svc.start_sandbox(plain_agent)
    with patch("src.fleet.app.sandbox.asyncio.create_subprocess_exec", return_value=_proc()), \
         patch("src.fleet.app.sandbox.shutil.rmtree"):
        await sandbox_svc.stop_sandbox(plain_agent)
    rec = await AgentRepo(conn).find_by_id(plain_agent)
    assert rec["status"] == "idle"
    assert rec["sandbox_id"] is None
