import asyncio
import shutil
import socket
from pathlib import Path
from uuid import UUID

from src.fleet.app.agents import AgentService
from src.fleet.app.vm_payload import build_vm_payload
from src.integrations.app import IntegrationsApp
from src.library.app import LibraryApp

_SANDBOX_WORKDIR = Path("/tmp/officeclaw")
_DEFAULT_IMAGE = "ghcr.io/hkuds/nanobot:latest"
_DEFAULT_CPUS = "1"
_DEFAULT_MEMORY = "512M"


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


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

        workdir = _SANDBOX_WORKDIR / str(agent_id)
        workdir.mkdir(parents=True, exist_ok=True)

        for f in payload["files"]:
            dest = workdir / f["path"]
            dest.parent.mkdir(parents=True, exist_ok=True)
            with open(dest, "w") as fh:
                fh.write(f["content"])

        with open(workdir / "config.json", "w") as fh:
            fh.write(payload["config_json"])

        sandbox_name = f"agent-{agent_id}"
        gateway_port = _find_free_port()
        cmd: list[str] = [
            "msb",
            "run",
            _DEFAULT_IMAGE,
            "--name",
            sandbox_name,
            "--detach",
            "--volume",
            f"{workdir}:/workspace",
            "--cpus",
            _DEFAULT_CPUS,
            "--memory",
            _DEFAULT_MEMORY,
            "-p",
            f"{gateway_port}:18790",
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

        await self._agents.update(
            agent_id,
            status="running",
            sandbox_id=sandbox_name,
            gateway_port=gateway_port,
        )
        return sandbox_name

    async def stop(self, agent_id: UUID) -> None:
        """Stop and remove msb sandbox, clean up workspace."""
        record = await self._agents.find_by_id(agent_id)
        if not record or not record["sandbox_id"]:
            raise ValueError(f"Agent {agent_id} has no running sandbox")

        sandbox_name = record["sandbox_id"]

        for subcmd in (
            ["msb", "stop", sandbox_name],
            ["msb", "rm", sandbox_name],
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

        await self._agents.update(agent_id, status="idle", sandbox_id=None, gateway_port=None)
