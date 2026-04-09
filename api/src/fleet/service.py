import asyncio
import shutil
from pathlib import Path
from uuid import UUID

import asyncpg

from src.fleet.repository import AgentRepo

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
        with open(dest, "w") as fh:
            fh.write(f["content"])

    with open(workdir / "config.json", "w") as fh:
        fh.write(payload["config_json"])

    sandbox_name = f"agent-{agent_id}"
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

    await AgentRepo(conn).update(agent_id, status="idle", sandbox_id=None)
