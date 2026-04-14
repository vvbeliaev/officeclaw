"""WorkspaceService — creates workspaces and runs per-workspace bootstrap."""
from __future__ import annotations

import re
import secrets
from typing import TYPE_CHECKING
from uuid import UUID

import asyncpg

from src.shared.config import get_settings

if TYPE_CHECKING:
    from src.fleet.app import FleetApp
    from src.integrations.app import IntegrationsApp
    from src.workspace.core.ports.outbound import IWorkspaceRepo

_SOUL_MD = """
You are the Admin agent for OfficeClaw -- a fleet manager AI that helps users
create, configure, and manage their personal AI agents.

You have access to the `officeclaw` MCP tool which allows you to perform all
fleet operations: creating agents, installing skills, configuring channels,
managing environment variables, and monitoring fleet status.

When the user asks you to do something with their agents, use the officeclaw
tools to make it happen. Be proactive and helpful. When creating agents,
suggest good names and configurations. When installing skills, explain what
the skill does.

Always confirm important actions (deleting agents, changing configurations)
before executing them.
"""

_AGENTS_MD = """
# Agents

You operate as a fleet manager. Your job is to help the user build and manage
their fleet of AI agents.

## Available MCP Tools
- officeclaw: Fleet management (create/start/stop/delete agents, manage skills, envs, channels)
"""

_TOOLS_MD = """
# Tools

## officeclaw MCP

Fleet management tool. Use it to:
- List agents: `list_agents`
- Create an agent: `create_agent(name, image?)`
- Start/stop an agent: `start_agent(agent_id)`, `stop_agent(agent_id)`
- Update files: `update_agent_file(agent_id, path, content)`
- Delete an agent: `delete_agent(agent_id)`
- Skills: `list_skills`, `create_skill(name, description?)`, `attach_skill(agent_id, skill_id)`
- Envs: `list_envs`, `create_env(name, values_json)`
- Channels: `list_channels`
- Fleet status: `get_fleet_status`
"""

_SLUG_RE = re.compile(r'^[a-z0-9][a-z0-9-]{1,62}[a-z0-9]$')


def validate_slug(slug: str) -> str | None:
    """Return error message if slug is invalid, else None."""
    if len(slug) < 3 or len(slug) > 64:
        return "Slug must be 3–64 characters"
    if not _SLUG_RE.match(slug):
        return "Slug may only contain lowercase letters, digits, and hyphens (no leading/trailing hyphens)"
    return None


class WorkspaceService:
    def __init__(
        self,
        repo: IWorkspaceRepo,
        fleet: FleetApp,
        integrations: IntegrationsApp,
    ) -> None:
        self._repo = repo
        self._fleet = fleet
        self._integrations = integrations

    async def create_workspace(self, user_id: UUID, name: str) -> asyncpg.Record:
        """Create workspace + run full bootstrap. Returns workspace record with token."""
        token = secrets.token_urlsafe(32)
        workspace = await self._repo.create(user_id, name, token)
        workspace_id = workspace["id"]
        await self._bootstrap(workspace_id, token)
        return workspace

    async def list_workspaces(self, user_id: UUID) -> list[asyncpg.Record]:
        return await self._repo.list_by_user(user_id)

    async def find_by_token(self, token: str) -> asyncpg.Record | None:
        return await self._repo.find_by_token(token)

    async def update_workspace(
        self,
        workspace_id: UUID,
        name: str | None,
        slug: str | None,
    ) -> asyncpg.Record:
        if slug is not None:
            err = validate_slug(slug)
            if err:
                raise ValueError(err)
        return await self._repo.update(workspace_id, name, slug)

    async def delete_workspace(self, workspace_id: UUID) -> None:
        await self._repo.delete(workspace_id)

    async def _bootstrap(self, workspace_id: UUID, token: str) -> None:
        """Create Admin agent and all seed resources for a new workspace."""
        settings = get_settings()

        default_llm_env = await self._integrations.create_env(
            workspace_id,
            "default-llm",
            {
                "OFFICECLAW_LLM_API_KEY": settings.default_llm_api_key,
                "OFFICECLAW_LLM_BASE_URL": settings.default_llm_base_url,
                "OFFICECLAW_LLM_MODEL": settings.default_llm_model,
            },
            category="llm-provider",
        )

        agent_record = await self._fleet.create_agent(
            workspace_id, "Admin", "localhost:5005/officeclaw/agent:latest", is_admin=True
        )
        agent_id = agent_record["id"]

        await self._fleet.upsert_file(agent_id, "SOUL.md", _SOUL_MD)
        await self._fleet.upsert_file(agent_id, "AGENTS.md", _AGENTS_MD)
        await self._fleet.upsert_file(agent_id, "TOOLS.md", _TOOLS_MD)

        mcp_url = f"{settings.mcp_base_url}/mcp/admin"
        mcp_record = await self._integrations.create_mcp(
            workspace_id,
            "officeclaw-admin",
            "http",
            {
                "url": mcp_url,
                "headers": {"Authorization": "Bearer ${OFFICECLAW_TOKEN}"},
            },
        )

        knowledge_mcp_url = f"{settings.mcp_base_url}/mcp/knowledge"
        await self._integrations.create_mcp(
            workspace_id,
            "officeclaw-knowledge",
            "http",
            {
                "url": knowledge_mcp_url,
                "headers": {"Authorization": "Bearer ${OFFICECLAW_TOKEN}"},
            },
        )
        # No attach — users connect it to agents themselves

        await self._integrations.attach_mcp(agent_id, mcp_record["id"])
        await self._integrations.attach_env(agent_id, default_llm_env["id"])
