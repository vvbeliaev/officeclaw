from __future__ import annotations

from typing import TYPE_CHECKING

import asyncpg

from src.identity.adapters.out.repository import UserRepo
from src.identity.app import IdentityApp
from src.identity.app.users import UserService

if TYPE_CHECKING:
    from src.workspace.app import WorkspaceApp


def build(pool: asyncpg.Pool, workspace: WorkspaceApp) -> IdentityApp:
    repo = UserRepo(pool)
    service = UserService(repo, workspace)
    return IdentityApp(service)
