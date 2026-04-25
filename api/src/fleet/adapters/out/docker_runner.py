"""Docker CLI sandbox runner — local dev backend."""

from __future__ import annotations

import asyncio
from pathlib import Path

_DEFAULT_CPUS = "1"
_DEFAULT_MEMORY_MIB = "512"
_GATEWAY_GUEST_PORT = "18790"


async def _run(*argv: str, capture: bool = True) -> tuple[int, bytes, bytes]:
    proc = await asyncio.create_subprocess_exec(
        *argv,
        stdout=asyncio.subprocess.PIPE if capture else asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE if capture else asyncio.subprocess.DEVNULL,
    )
    stdout, stderr = await proc.communicate()
    return proc.returncode or 0, stdout, stderr


class DockerRunner:
    async def start(
        self,
        *,
        name: str,
        image: str,
        workdir: Path,
        gateway_port: int,
        env: dict[str, str],
    ) -> None:
        argv = [
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
            f"{_DEFAULT_MEMORY_MIB}m",
            "-p",
            f"{gateway_port}:{_GATEWAY_GUEST_PORT}",
        ]
        for k, v in env.items():
            argv += ["-e", f"{k}={v}"]
        argv.append(image)
        rc, _, stderr = await _run(*argv)
        if rc != 0:
            raise RuntimeError(f"docker run failed: {stderr.decode()}")

    async def stop(self, name: str) -> None:
        await _run("docker", "stop", name)

    async def remove(self, name: str) -> None:
        await _run("docker", "rm", name)

    async def force_remove(self, name: str) -> None:
        await _run("docker", "rm", "-f", name, capture=False)

    async def is_alive(self, name: str) -> bool:
        try:
            rc, stdout, _ = await _run(
                "docker", "inspect", "--format", "{{.State.Status}}", name
            )
            return rc == 0 and stdout.decode().strip() == "running"
        except Exception:
            return False

    async def capture_logs(self, name: str, tail: int = 80) -> str:
        try:
            _, stdout, _ = await _run("docker", "logs", "--tail", str(tail), name)
            return stdout.decode(errors="replace").strip() or "(no output)"
        except Exception as exc:
            return f"(failed to collect logs: {exc})"
