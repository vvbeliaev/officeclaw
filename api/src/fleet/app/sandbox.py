import asyncio
import logging
import shutil
import socket
from pathlib import Path
from uuid import UUID

import httpx

from src.fleet.app.agents import AgentService
from src.fleet.app.vm_payload import build_vm_payload
from src.integrations.app import IntegrationsApp
from src.library.app import LibraryApp
from src.shared.config import get_settings

_log = logging.getLogger(__name__)

_DEFAULT_IMAGE = "localhost:5005/officeclaw/agent:latest"


def _sandbox_workdir(agent_id: UUID) -> Path:
    """Return the resolved host path for an agent's sandbox workspace.

    `Path.expanduser()` handles a leading ~, and `.resolve()` follows any
    symlinks (important on macOS where /tmp → /private/tmp — Docker Desktop's
    file-sharing list matches by real path).
    """
    root = Path(get_settings().sandbox_workdir).expanduser().resolve()
    return root / str(agent_id)


_SYNC_EXCLUDE_TOP = {
    "config.json",
    "skills",
    ".git",
    ".gitignore",
    ".traces",
    # Runtime files are assembled fresh on every start (templates + user override).
    # Never sync them back — the workspace copy is merged/ephemeral.
    "SOUL.md",
    "AGENTS.md",
    "HEARTBEAT.md",
    "TOOLS.md",
    "USER.md",
}
_DEFAULT_CPUS = "1"
_DEFAULT_MEMORY = "512"  # MiB
_GATEWAY_READY_TIMEOUT = 60  # seconds to wait for nanobot gateway to be ready
_GATEWAY_READY_INTERVAL = 0.5


def _run_cmd(
    image: str, name: str, workdir: Path, gateway_port: int, env: dict
) -> list[str]:
    runner = get_settings().sandbox_runner
    if runner == "docker":
        cmd = [
            "docker",
            "run",
            "--name",
            name,
            "--detach",
            "--volume",
            f"{workdir}:/workspace",
            "--cpus",
            _DEFAULT_CPUS,
            "--memory",
            f"{_DEFAULT_MEMORY}m",  # Docker expects "512m"
            "-p",
            f"{gateway_port}:18790",
        ]
        for k, v in env.items():
            cmd += ["-e", f"{k}={v}"]
        cmd.append(image)
    else:
        cmd = [
            "msb",
            "run",
            image,
            "--name",
            name,
            "--detach",
            "--volume",
            f"{workdir}:/workspace",
            "--cpus",
            _DEFAULT_CPUS,
            "--memory",
            _DEFAULT_MEMORY,  # msb expects plain integer
            "-p",
            f"{gateway_port}:18790",
        ]
        for k, v in env.items():
            cmd += ["-e", f"{k}={v}"]
    return cmd


def _stop_cmd(name: str) -> list[str]:
    runner = get_settings().sandbox_runner
    return ["docker", "stop", name] if runner == "docker" else ["msb", "stop", name]


def _rm_cmd(name: str) -> list[str]:
    runner = get_settings().sandbox_runner
    return ["docker", "rm", name] if runner == "docker" else ["msb", "rm", name]


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


def _force_rm_cmd(name: str) -> list[str]:
    """Command to force-remove a sandbox by name, regardless of its state."""
    runner = get_settings().sandbox_runner
    if runner == "docker":
        return ["docker", "rm", "-f", name]
    return ["msb", "rm", "--force", name]


async def _force_rm_sandbox(name: str) -> None:
    """Best-effort removal of an existing sandbox with the given name.

    Used before `start` to clean up orphans left behind by a previous
    crashed or aborted run. Ignores failures — the target may not exist.
    """
    proc = await asyncio.create_subprocess_exec(
        *_force_rm_cmd(name),
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    await proc.communicate()


def gateway_base_url(port: int) -> str:
    """Return the base URL to reach a nanobot gateway at the given port."""
    return f"http://{get_settings().sandbox_gateway_host}:{port}"


async def _capture_logs(name: str, tail: int = 80) -> str:
    """Best-effort fetch of container/sandbox logs for error reporting."""
    runner = get_settings().sandbox_runner
    if runner == "docker":
        cmd = ["docker", "logs", "--tail", str(tail), name]
    else:
        cmd = ["msb", "logs", "--tail", str(tail), name]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await proc.communicate()
        return stdout.decode(errors="replace").strip() or "(no output)"
    except Exception as exc:
        return f"(failed to collect logs: {exc})"


async def _is_sandbox_alive(name: str) -> bool:
    """Return True if the named container is in the 'running' state."""
    runner = get_settings().sandbox_runner
    if runner == "docker":
        cmd = ["docker", "inspect", "--format", "{{.State.Status}}", name]
    else:
        # msb: exits 0 and prints "running" when alive, non-zero otherwise
        cmd = ["msb", "inspect", "--format", "{{.State.Status}}", name]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await proc.communicate()
        return proc.returncode == 0 and stdout.decode().strip() == "running"
    except Exception:
        return False


def _read_workspace_files(workdir: Path) -> list[dict]:
    """Recursively read all workspace files, excluding generated/managed dirs."""
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
        result.append({"path": str(rel), "content": content})
    return result


async def _wait_for_gateway(port: int, sandbox_name: str) -> None:
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
            ) as exc:
                last_error = exc
                await asyncio.sleep(_GATEWAY_READY_INTERVAL)
    logs = await _capture_logs(sandbox_name)
    raise RuntimeError(
        f"Gateway on port {port} did not become ready in "
        f"{_GATEWAY_READY_TIMEOUT}s (last error: {last_error}).\n\n"
        f"── sandbox logs ──\n{logs}"
    )


class SandboxService:
    """App-layer service: manages sandbox lifecycle via msb CLI."""

    def __init__(
        self,
        agents: AgentService,
        integrations: IntegrationsApp,
        skills: LibraryApp,
    ) -> None:
        self._agents = agents
        self._integrations = integrations
        self._skills = skills

    async def start(self, agent_id: UUID) -> str:
        """Build VM payload, write workspace, launch msb sandbox. Returns sandbox_id."""
        payload = await build_vm_payload(
            agent_id, self._agents, self._integrations, self._skills
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
            # Atomic swap: remove stale workdir (orphan from a previous crash),
            # then rename tmp into place — rename() is atomic on POSIX.
            if workdir.exists():
                shutil.rmtree(workdir)
            tmp_workdir.rename(workdir)
        except Exception:
            shutil.rmtree(tmp_workdir, ignore_errors=True)
            raise

        sandbox_name = f"agent-{agent_id}"

        # Clean up any orphan container from a previous crashed / aborted
        # run — otherwise `docker run --name X` fails with a name conflict.
        await _force_rm_sandbox(sandbox_name)

        gateway_port = _find_free_port()
        cmd = _run_cmd(
            image=_DEFAULT_IMAGE,
            name=sandbox_name,
            workdir=workdir,
            gateway_port=gateway_port,
            env=payload["env"],
        )

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            runner = get_settings().sandbox_runner
            raise RuntimeError(f"{runner} run failed: {stderr.decode()}")

        # If the gateway never comes up, tear the container down before
        # surfacing the error so we don't leave a broken sandbox behind.
        try:
            await _wait_for_gateway(gateway_port, sandbox_name)
        except Exception:
            await _force_rm_sandbox(sandbox_name)
            raise

        await self._agents.update(
            agent_id,
            status="running",
            sandbox_id=sandbox_name,
            gateway_port=gateway_port,
        )
        return sandbox_name

    async def stop(self, agent_id: UUID) -> None:
        """Stop sandbox, sync mutable files back to Postgres, remove sandbox and workspace."""
        record = await self._agents.find_by_id(agent_id)
        if not record or not record["sandbox_id"]:
            raise ValueError(f"Agent {agent_id} has no running sandbox")

        sandbox_name = record["sandbox_id"]

        proc = await asyncio.create_subprocess_exec(
            *_stop_cmd(sandbox_name),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()

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

        proc = await asyncio.create_subprocess_exec(
            *_rm_cmd(sandbox_name),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()

        if workdir.exists():
            shutil.rmtree(workdir, ignore_errors=True)

        await self._agents.update(
            agent_id, status="idle", sandbox_id=None, gateway_port=None
        )

    async def _sync_agent_files(self, agent_id: UUID) -> None:
        """Read mutable workspace files from disk and upsert into Postgres."""
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
            if await _is_sandbox_alive(sandbox_name):
                continue
            agent_id: UUID = agent["id"]
            _log.warning(
                "Sandbox %s is dead; marking agent %s as error", sandbox_name, agent_id
            )
            try:
                await self._sync_agent_files(agent_id)
            except Exception:
                _log.exception("Failed to sync files for crashed agent %s", agent_id)
            await _force_rm_sandbox(sandbox_name)
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
