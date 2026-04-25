from __future__ import annotations

from typing import TYPE_CHECKING

import asyncpg

from src.workspace.adapters.out.repository import WorkspaceRepo
from src.workspace.app import WorkspaceApp
from src.workspace.app.workspaces import WorkspaceService

if TYPE_CHECKING:
    from src.fleet.app import FleetApp
    from src.integrations.app import IntegrationsApp
    from src.library.app import LibraryApp


def build(
    pool: asyncpg.Pool,
    fleet: FleetApp,
    integrations: IntegrationsApp,
    library: LibraryApp,
) -> WorkspaceApp:
    repo = WorkspaceRepo(pool)
    service = WorkspaceService(repo, fleet, integrations, library)
    return WorkspaceApp(service)
