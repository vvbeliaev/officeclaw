import asyncio
import logging
import shutil
import socket
from pathlib import Path
from uuid import UUID

import httpx

from src.fleet.app.agents import AgentService
from src.fleet.app.vm_payload import build_vm_payload
from src.fleet.core.ports.out import ISandboxRunner
from src.fleet.core.runtime_files import RUNTIME_PATHS, extract_override
from src.integrations.app import IntegrationsApp
from src.library.app import LibraryApp
from src.shared.config import get_settings

_log = logging.getLogger(__name__)

_DEFAULT_IMAGE = "localhost:5005/officeclaw/agent:latest"

_SYNC_EXCLUDE_TOP = {
    "config.json",
    "skills",
    ".git",
    ".gitignore",
    ".traces",
}
_GATEWAY_READY_TIMEOUT = 60
_GATEWAY_READY_INTERVAL = 0.5


def _sandbox_workdir(agent_id: UUID) -> Path:
    """Resolved host path for an agent's sandbox workspace.

    `.resolve()` follows symlinks (matters on macOS where /tmp → /private/tmp,
    which Docker Desktop's file-sharing matches by real path).
    """
    root = Path(get_settings().sandbox_workdir).expanduser().resolve()
    return root / str(agent_id)


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


def gateway_base_url(port: int) -> str:
    return f"http://{get_settings().sandbox_gateway_host}:{port}"


def _read_workspace_files(workdir: Path) -> list[dict]:
    """Recursively read mutable workspace files, excluding generated dirs.

    Runtime files (SOUL.md / USER.md / AGENTS.md / HEARTBEAT.md / TOOLS.md)
    are split on the template-boundary marker so only the per-agent override
    is persisted back to agent_files. If the marker is absent (no template
    attached at start, or the agent wiped the marker), the full body is
    treated as override.
    """
    result = []
    for path in sorted(workdir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(workdir)
        if rel.parts[0] in _SYNC_EXCLUDE_TOP:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            continue
        rel_str = str(rel)
        if rel_str in RUNTIME_PATHS:
            content = extract_override(content)
            if not content:
                continue
        result.append({"path": rel_str, "content": content})
    return result


async def _wait_for_gateway(
    runner: ISandboxRunner, port: int, sandbox_name: str
) -> None:
    """Poll nanobot gateway until it accepts an HTTP response or times out.

    During boot we tolerate any transport-level failure — `ConnectError`
    (port not bound yet), `ReadError` (server accepted but hung up), and
    `RemoteProtocolError` (server accepted then closed without a reply,
    common while nanobot is still wiring up its HTTP handlers).
    """
    deadline = asyncio.get_event_loop().time() + _GATEWAY_READY_TIMEOUT
    last_error: Exception | None = None
    async with httpx.AsyncClient(timeout=1.0) as client:
        while asyncio.get_event_loop().time() < deadline:
            try:
                await client.get(gateway_base_url(port))
                return
            except (
                httpx.ConnectError,
                httpx.ReadError,
                httpx.RemoteProtocolError,
                httpx.ReadTimeout,
            ) as err:
                last_error = err
                await asyncio.sleep(_GATEWAY_READY_INTERVAL)
    logs = await runner.capture_logs(sandbox_name)
    raise RuntimeError(
        f"Gateway on port {port} did not become ready in "
        f"{_GATEWAY_READY_TIMEOUT}s (last error: {last_error}).\n\n"
        f"── sandbox logs ──\n{logs}"
    )


class SandboxService:
    """App-layer service: manages sandbox lifecycle via an ISandboxRunner."""

    def __init__(
        self,
        agents: AgentService,
        integrations: IntegrationsApp,
        skills: LibraryApp,
        runner: ISandboxRunner,
    ) -> None:
        self._agents = agents
        self._integrations = integrations
        self._skills = skills
        self._runner = runner

    async def start(
        self, agent_id: UUID, workspace_token: str, timezone: str
    ) -> str:
        """Build VM payload, write workspace, launch sandbox. Returns sandbox_id.

        `workspace_token` and `timezone` are passed in by the caller (route /
        MCP handler) after it has resolved the agent's workspace and owning
        user — fleet intentionally does not know how to look those up.
        """
        payload = await build_vm_payload(
            agent_id,
            self._agents,
            self._integrations,
            self._skills,
            workspace_token,
            timezone,
        )

        workdir = _sandbox_workdir(agent_id)
        tmp_workdir = workdir.parent / f".tmp-{agent_id}"
        try:
            tmp_workdir.mkdir(parents=True, exist_ok=True)
            for f in payload["files"]:
                dest = tmp_workdir / f["path"]
                dest.parent.mkdir(parents=True, exist_ok=True)
                with open(dest, "w") as fh:
                    fh.write(f["content"])
            with open(tmp_workdir / "config.json", "w") as fh:
                fh.write(payload["config_json"])
            # Atomic swap: drop stale workdir (orphan from a previous crash),
            # then rename tmp into place — rename() is atomic on POSIX.
            if workdir.exists():
                shutil.rmtree(workdir)
            tmp_workdir.rename(workdir)
        except Exception:
            shutil.rmtree(tmp_workdir, ignore_errors=True)
            raise

        sandbox_name = f"agent-{agent_id}"

        # Best-effort cleanup of any orphan sandbox under the same name —
        # otherwise `start` will collide on the name.
        await self._runner.force_remove(sandbox_name)

        gateway_port = _find_free_port()
        await self._runner.start(
            name=sandbox_name,
            image=_DEFAULT_IMAGE,
            workdir=workdir,
            gateway_port=gateway_port,
            env=payload["env"],
        )

        # If the gateway never comes up, tear the sandbox down before
        # surfacing the error so we don't leave a broken VM behind.
        try:
            await _wait_for_gateway(self._runner, gateway_port, sandbox_name)
        except Exception:
            await self._runner.force_remove(sandbox_name)
            raise

        await self._agents.update(
            agent_id,
            status="running",
            sandbox_id=sandbox_name,
            gateway_port=gateway_port,
        )
        return sandbox_name

    async def stop(self, agent_id: UUID) -> None:
        """Stop sandbox, sync mutable files back to Postgres, remove sandbox + workspace."""
        record = await self._agents.find_by_id(agent_id)
        if not record or not record["sandbox_id"]:
            raise ValueError(f"Agent {agent_id} has no running sandbox")

        sandbox_name = record["sandbox_id"]
        await self._runner.stop(sandbox_name)

        # Sync mutable workspace files back to Postgres — best-effort, must not
        # block the cleanup steps that follow.
        workdir = _sandbox_workdir(agent_id)
        try:
            synced = _read_workspace_files(workdir)
            if synced:
                await self._agents.bulk_upsert_files(agent_id, synced)
        except Exception:
            _log.exception(
                "Failed to sync workspace files for agent %s during stop", agent_id
            )

        await self._runner.remove(sandbox_name)

        if workdir.exists():
            shutil.rmtree(workdir, ignore_errors=True)

        await self._agents.update(
            agent_id, status="idle", sandbox_id=None, gateway_port=None
        )

    async def _sync_agent_files(self, agent_id: UUID) -> None:
        workdir = _sandbox_workdir(agent_id)
        files = _read_workspace_files(workdir)
        if files:
            await self._agents.bulk_upsert_files(agent_id, files)

    async def check_health(self) -> None:
        """One-shot pass: mark crashed/missing sandboxes as error and sync their files."""
        running = await self._agents.list_running()
        for agent in running:
            sandbox_name = agent["sandbox_id"]
            if not sandbox_name:
                continue
            if await self._runner.is_alive(sandbox_name):
                continue
            agent_id: UUID = agent["id"]
            _log.warning(
                "Sandbox %s is dead; marking agent %s as error", sandbox_name, agent_id
            )
            try:
                await self._sync_agent_files(agent_id)
            except Exception:
                _log.exception("Failed to sync files for crashed agent %s", agent_id)
            await self._runner.force_remove(sandbox_name)
            workdir = _sandbox_workdir(agent_id)
            if workdir.exists():
                shutil.rmtree(workdir, ignore_errors=True)
            await self._agents.update(
                agent_id, status="error", sandbox_id=None, gateway_port=None
            )

    async def sync_all(self) -> None:
        """One-shot pass: persist mutable workspace files for all running agents."""
        running = await self._agents.list_running()
        for agent in running:
            try:
                await self._sync_agent_files(agent["id"])
            except Exception:
                _log.exception("Failed to sync files for agent %s", agent["id"])
