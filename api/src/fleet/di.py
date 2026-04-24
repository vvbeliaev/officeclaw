from __future__ import annotations

from typing import TYPE_CHECKING

import asyncpg

from src.fleet.adapters._in.watchers import SandboxWatcher
from src.fleet.adapters.out.repository import AgentFileRepo, AgentRepo
from src.fleet.app import FleetApp
from src.fleet.app.agents import AgentService
from src.fleet.app.sandbox import SandboxService
from src.integrations.app import IntegrationsApp
from src.library.app import LibraryApp

if TYPE_CHECKING:
    from src.workspace.app import WorkspaceApp


def build(
    pool: asyncpg.Pool,
    integrations: IntegrationsApp,
    library: LibraryApp,
) -> tuple[FleetApp, SandboxService, SandboxWatcher]:
    agents = AgentService(AgentRepo(pool), AgentFileRepo(pool))
    sandbox = SandboxService(agents, integrations, library)
    return FleetApp(agents, sandbox, integrations), sandbox, SandboxWatcher(sandbox)


def bind_workspace(sandbox: SandboxService, workspace: WorkspaceApp) -> None:
    """Complete the fleet↔workspace wiring after workspace_di.build runs."""
    sandbox.bind_workspace(workspace)
