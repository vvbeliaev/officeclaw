"""
OfficeClaw MCP server — fleet configuration tools for the Admin agent.

Mounted at /mcp in the FastAPI app. All tools are scoped to the authenticated
user via OFFICECLAW_TOKEN bearer auth.

Tool modules:
  agents      — fleet overview, create agent
  skills      — skill library + attach to agent
  envs        — env configs + attach to agent
  channels    — channel integrations + attach to agent
  mcp_servers — user MCP server configs + attach to agent
  templates   — user templates + attach to agent
"""

import logging
from uuid import UUID

import asyncpg
from fastmcp import FastMCP
from fastmcp.server.context import Context

from src.fleet.app import FleetApp
from src.identity.app import IdentityApp
from src.integrations.app import IntegrationsApp
from src.knowledge.app import KnowledgeApp
from src.library.app import LibraryApp

logger = logging.getLogger(__name__)

mcp = FastMCP("OfficeClaw")

_pool: asyncpg.Pool | None = None
_fleet: FleetApp | None = None
_identity: IdentityApp | None = None
_library: LibraryApp | None = None
_integrations: IntegrationsApp | None = None
_knowledge: KnowledgeApp | None = None


def setup(
    pool: asyncpg.Pool,
    fleet: FleetApp,
    identity: IdentityApp,
    library: LibraryApp,
    integrations: IntegrationsApp,
    knowledge: KnowledgeApp,
) -> None:
    global _pool, _fleet, _identity, _library, _integrations, _knowledge
    _pool = pool
    _fleet = fleet
    _identity = identity
    _library = library
    _integrations = integrations
    _knowledge = knowledge


def _assert_ready() -> None:
    if _pool is None:
        raise RuntimeError("MCP not initialised — call setup() first")


async def _require_user(context: Context) -> UUID:
    """Extract and validate bearer token → return user_id."""
    _assert_ready()
    request = context.request_context.request
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        raise ValueError("Missing or malformed Authorization header")
    token = auth[7:]
    assert _identity is not None
    record = await _identity.find_by_token(token)
    if not record:
        raise ValueError("Invalid OFFICECLAW_TOKEN")
    return record["id"]


# Import tool modules last to trigger @mcp.tool() registration
from . import agents, channels, envs, knowledge, mcp_servers, skills, templates  # noqa: E402, F401
