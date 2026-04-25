import asyncpg

from src.fleet.adapters._in.watchers import SandboxWatcher
from src.fleet.adapters.out.docker_runner import DockerRunner
from src.fleet.adapters.out.repository import AgentFileRepo, AgentRepo
from src.fleet.app import FleetApp
from src.fleet.app.agents import AgentService
from src.fleet.app.sandbox import SandboxService
from src.fleet.core.ports.out import ISandboxRunner
from src.integrations.app import IntegrationsApp
from src.library.app import LibraryApp
from src.shared.config import get_settings


def _build_runner() -> ISandboxRunner:
    """Pick a sandbox runner based on settings.

    `msb` (microsandbox SDK) requires KVM and a Linux/aarch64-or-Apple-Silicon
    wheel — installed via the `microsandbox` extra. On platforms where the
    wheel is unavailable (e.g. darwin x86_64) keep `SANDBOX_RUNNER=docker`
    so the SDK is never imported.
    """
    if get_settings().sandbox_runner == "docker":
        return DockerRunner()
    from src.fleet.adapters.out.microsandbox_runner import MicrosandboxRunner

    return MicrosandboxRunner()


def build(
    pool: asyncpg.Pool,
    integrations: IntegrationsApp,
    library: LibraryApp,
) -> tuple[FleetApp, SandboxWatcher]:
    agents = AgentService(AgentRepo(pool), AgentFileRepo(pool))
    runner = _build_runner()
    sandbox = SandboxService(agents, integrations, library, runner)
    return FleetApp(agents, sandbox, integrations), SandboxWatcher(sandbox)
