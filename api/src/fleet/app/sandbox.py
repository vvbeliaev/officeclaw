import asyncio
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

_DEFAULT_IMAGE = "localhost:5005/officeclaw/agent:latest"


def _sandbox_workdir(agent_id: UUID) -> Path:
    """Return the resolved host path for an agent's sandbox workspace.

    `Path.expanduser()` handles a leading ~, and `.resolve()` follows any
    symlinks (important on macOS where /tmp → /private/tmp — Docker Desktop's
    file-sharing list matches by real path).
    """
    root = Path(get_settings().sandbox_workdir).expanduser().resolve()
    return root / str(agent_id)
_MUTABLE_PATHS = (
    "SOUL.md",
    "USER.md",
    "memory/MEMORY.md",
    "memory/history.jsonl",
    "memory/.cursor",
    "memory/.dream_cursor",
    "cron/jobs.json",
)
_DEFAULT_CPUS = "1"
_DEFAULT_MEMORY = "512"  # MiB
_GATEWAY_READY_TIMEOUT = 15  # seconds to wait for nanobot gateway to be ready
_GATEWAY_READY_INTERVAL = 0.5


def _run_cmd(
    image: str, name: str, workdir: Path, gateway_port: int, env: dict
) -> list[str]:
    runner = get_settings().sandbox_runner
    if runner == "docker":
        cmd = [
            "docker", "run",
            "--name", name,
            "--detach",
            "--volume", f"{workdir}:/workspace",
            "--cpus", _DEFAULT_CPUS,
            "--memory", f"{_DEFAULT_MEMORY}m",  # Docker expects "512m"
            "-p", f"{gateway_port}:18790",
        ]
        for k, v in env.items():
            cmd += ["-e", f"{k}={v}"]
        cmd.append(image)
    else:
        cmd = [
            "msb", "run", image,
            "--name", name,
            "--detach",
            "--volume", f"{workdir}:/workspace",
            "--cpus", _DEFAULT_CPUS,
            "--memory", _DEFAULT_MEMORY,  # msb expects plain integer
            "-p", f"{gateway_port}:18790",
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
        payload = await build_vm_payload(agent_id, self._agents, self._integrations, self._skills)

        workdir = _sandbox_workdir(agent_id)
        workdir.mkdir(parents=True, exist_ok=True)

        for f in payload["files"]:
            dest = workdir / f["path"]
            dest.parent.mkdir(parents=True, exist_ok=True)
            with open(dest, "w") as fh:
                fh.write(f["content"])

        with open(workdir / "config.json", "w") as fh:
            fh.write(payload["config_json"])

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

        # Sync mutable workspace files back to Postgres before the volume is removed
        workdir = _sandbox_workdir(agent_id)
        synced: list[dict] = []
        for rel_path in _MUTABLE_PATHS:
            full_path = workdir / rel_path
            if full_path.exists():
                synced.append({"path": rel_path, "content": full_path.read_text()})
        if synced:
            await self._agents.bulk_upsert_files(agent_id, synced)

        proc = await asyncio.create_subprocess_exec(
            *_rm_cmd(sandbox_name),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()

        if workdir.exists():
            shutil.rmtree(workdir)

        await self._agents.update(agent_id, status="idle", sandbox_id=None, gateway_port=None)
