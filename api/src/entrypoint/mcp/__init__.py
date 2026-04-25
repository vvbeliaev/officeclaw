"""
OfficeClaw MCP servers — two endpoints sharing the same app state.

  /mcp/admin     — fleet management tools (Admin agent only)
  /mcp/knowledge — knowledge graph tools (all agents)

All tools are scoped to the authenticated workspace via OFFICECLAW_TOKEN bearer auth.

Tool modules (admin), grouped by the agent triad:

  Identity        — agents (CRUD, files), templates (workspace-shared SOUL/AGENTS/etc.)
  Capabilities    — skills, envs, mcp_servers
  Triggers        — crons, channels, agent.heartbeat (via update_agent)

Each resource follows the same workspace-resource → attach pattern:
  list_*  — read all in workspace
  get_*   — read one
  create_*/update_*/delete_*  — mutate workspace resource
  attach_*/detach_*  — link/unlink to a specific agent

Tool modules (knowledge):
  knowledge   — ingest_knowledge, query_knowledge
"""

import logging
from uuid import UUID

import asyncpg
from fastmcp import FastMCP
from fastmcp.server.context import Context

from src.fleet.app import FleetApp
from src.workspace.app import WorkspaceApp
from src.integrations.app import IntegrationsApp
from src.knowledge.app import KnowledgeApp
from src.library.app import LibraryApp

logger = logging.getLogger(__name__)

admin_mcp = FastMCP("OfficeClaw-Admin")
knowledge_mcp = FastMCP("OfficeClaw-Knowledge")

_pool: asyncpg.Pool | None = None
_fleet: FleetApp | None = None
_workspace: WorkspaceApp | None = None
_library: LibraryApp | None = None
_integrations: IntegrationsApp | None = None
_knowledge: KnowledgeApp | None = None


def setup(
    pool: asyncpg.Pool,
    fleet: FleetApp,
    workspace: WorkspaceApp,
    library: LibraryApp,
    integrations: IntegrationsApp,
    knowledge: KnowledgeApp | None = None,
) -> None:
    global _pool, _fleet, _workspace, _library, _integrations, _knowledge
    _pool = pool
    _fleet = fleet
    _workspace = workspace
    _library = library
    _integrations = integrations
    _knowledge = knowledge


def _assert_ready() -> None:
    if _pool is None:
        raise RuntimeError("MCP not initialised — call setup() first")


async def _require_workspace(context: Context) -> UUID:
    """Extract and validate bearer token → return workspace_id."""
    _assert_ready()
    request = context.request_context.request
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        raise ValueError("Missing or malformed Authorization header")
    token = auth[7:]
    assert _workspace is not None
    record = await _workspace.find_by_token(token)
    if not record:
        raise ValueError("Invalid OFFICECLAW_TOKEN")
    return record["id"]  # workspace id


# Import tool modules last to trigger @admin_mcp.tool() / @knowledge_mcp.tool() registration
from . import agents, channels, crons, envs, knowledge, mcp_servers, skills, templates  # noqa: E402, F401
