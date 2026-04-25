"""Microsandbox SDK sandbox runner — production microVM backend.

Lives behind a feature flag (`SANDBOX_RUNNER=msb`). Imports microsandbox
lazily so the adapter file is importable on platforms where the SDK
wheel is unavailable (notably darwin x86_64) — the import only happens
when the runner is actually instantiated.
"""

from __future__ import annotations

import asyncio
from collections import deque
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from microsandbox import ExecHandle

_DEFAULT_CPUS = 1
_DEFAULT_MEMORY_MIB = 512
_GATEWAY_GUEST_PORT = 18790
_LOG_BUFFER_LINES = 1000

# Nanobot entrypoint+cmd from sandbox/Dockerfile (ENTRYPOINT/CMD do not
# auto-run inside microsandbox — VMs boot empty and we exec the agent
# process ourselves).
_NANOBOT_CMD = "nanobot"
_NANOBOT_ARGS = [
    "gateway",
    "--config",
    "/workspace/config.json",
    "--workspace",
    "/workspace",
]


class MicrosandboxRunner:
    """ISandboxRunner implementation backed by the microsandbox Python SDK.

    Tracks live sandbox + nanobot exec handle in-process. On api restart
    any orphan microVMs surface to `SandboxService.check_health` as dead
    (no in-memory entry) and are reaped.
    """

    def __init__(self) -> None:
        # Lazy import: SDK is not installable on darwin_x86_64 dev machines.
        from microsandbox import Network, Sandbox, Volume  # noqa: PLC0415

        self._Sandbox = Sandbox
        self._Volume = Volume
        self._Network = Network
        self._state: dict[str, dict[str, Any]] = {}

    async def start(
        self,
        *,
        name: str,
        image: str,
        workdir: Path,
        gateway_port: int,
        env: dict[str, str],
    ) -> None:
        sandbox = await self._Sandbox.create(
            name,
            image=image,
            cpus=_DEFAULT_CPUS,
            memory=_DEFAULT_MEMORY_MIB,
            volumes={"/workspace": self._Volume.bind(str(workdir))},
            ports={gateway_port: _GATEWAY_GUEST_PORT},
            env=env,
            # allow_all: agent must reach our api over private LAN/host for
            # MCP callbacks. Tighten with a custom NetworkPolicy once the
            # api endpoint is reachable via a stable public address.
            network=self._Network.allow_all(),
            replace=True,
        )

        log_buffer: deque[bytes] = deque(maxlen=_LOG_BUFFER_LINES)
        try:
            handle = await sandbox.exec_stream(_NANOBOT_CMD, _NANOBOT_ARGS)
        except Exception:
            await self._safe_remove(name)
            raise

        drain_task = asyncio.create_task(_drain(handle, log_buffer))
        self._state[name] = {
            "sandbox": sandbox,
            "handle": handle,
            "logs": log_buffer,
            "drain": drain_task,
        }

    async def stop(self, name: str) -> None:
        entry = self._state.get(name)
        if entry:
            try:
                await entry["handle"].kill()
            except Exception:
                pass
            try:
                await entry["sandbox"].stop_and_wait()
            except Exception:
                pass
            entry["drain"].cancel()
        else:
            # Recover lost in-memory state — sandbox may still exist.
            try:
                handle = await self._Sandbox.get(name)
                await handle.stop()
            except Exception:
                pass

    async def remove(self, name: str) -> None:
        await self._safe_remove(name)
        self._state.pop(name, None)

    async def force_remove(self, name: str) -> None:
        entry = self._state.pop(name, None)
        if entry:
            try:
                await entry["handle"].kill()
            except Exception:
                pass
            entry["drain"].cancel()
            try:
                await entry["sandbox"].kill()
            except Exception:
                pass
        await self._safe_remove(name)

    async def is_alive(self, name: str) -> bool:
        try:
            handle = await self._Sandbox.get(name)
            return str(handle.status).upper().endswith("RUNNING")
        except Exception:
            return False

    async def capture_logs(self, name: str, tail: int = 80) -> str:
        entry = self._state.get(name)
        if not entry:
            return "(no in-memory log buffer for sandbox)"
        lines = list(entry["logs"])[-tail:]
        if not lines:
            return "(no output)"
        return b"\n".join(lines).decode(errors="replace")

    async def _safe_remove(self, name: str) -> None:
        try:
            await self._Sandbox.remove(name)
        except Exception:
            pass


async def _drain(handle: ExecHandle, buffer: deque[bytes]) -> None:
    """Tee nanobot stdout/stderr into the per-sandbox ring buffer."""
    try:
        async for event in handle:
            if event.event_type in ("stdout", "stderr") and event.data:
                buffer.append(event.data.rstrip(b"\n"))
            elif event.event_type == "exited":
                break
    except asyncio.CancelledError:
        raise
    except Exception:
        pass
