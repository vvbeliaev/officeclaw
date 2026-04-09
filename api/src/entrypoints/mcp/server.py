"""
OfficeClaw MCP server — fleet management tools for the Admin agent.

Mounted at /mcp in the FastAPI app. All tools are scoped to the authenticated
user via OFFICECLAW_TOKEN bearer auth.

Pattern: each tool has a corresponding mcp_<name>(deps, user_id, ...) business
logic function. Tests call these directly. The @mcp.tool() wrappers are thin
— they validate auth and delegate.
"""

import json
import logging
from uuid import UUID

import asyncpg
from fastmcp import FastMCP
from fastmcp.server.context import Context

from src.fleet.app import FleetApp
from src.identity.app import IdentityApp
from src.integrations.app import IntegrationsApp
from src.library.app import LibraryApp

logger = logging.getLogger(__name__)

mcp = FastMCP("OfficeClaw")

_pool: asyncpg.Pool | None = None
_fleet: FleetApp | None = None
_identity: IdentityApp | None = None
_library: LibraryApp | None = None
_integrations: IntegrationsApp | None = None


def setup(
    pool: asyncpg.Pool,
    fleet: FleetApp,
    identity: IdentityApp,
    library: LibraryApp,
    integrations: IntegrationsApp,
) -> None:
    global _pool, _fleet, _identity, _library, _integrations
    _pool = pool
    _fleet = fleet
    _identity = identity
    _library = library
    _integrations = integrations


def _assert_ready() -> None:
    if _pool is None:
        raise RuntimeError("MCP not initialised — call setup() first")


# Auth helper


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


# Business logic functions (tested directly)


async def mcp_list_agents(fleet: FleetApp, user_id: UUID) -> list[dict]:
    records = await fleet.list_agents(user_id)
    return [
        {
            "id": str(r["id"]),
            "name": r["name"],
            "status": r["status"],
            "is_admin": r["is_admin"],
            "image": r["image"],
        }
        for r in records
    ]


async def mcp_get_fleet_status(fleet: FleetApp, user_id: UUID) -> dict:
    records = await fleet.list_agents(user_id)
    agents = [
        {
            "id": str(r["id"]),
            "name": r["name"],
            "status": r["status"],
            "is_admin": r["is_admin"],
        }
        for r in records
    ]
    summary: dict[str, int] = {"idle": 0, "running": 0, "error": 0}
    for a in agents:
        summary[a["status"]] = summary.get(a["status"], 0) + 1
    return {"agents": agents, "summary": summary}


async def mcp_create_agent(
    fleet: FleetApp, user_id: UUID, name: str, image: str
) -> dict:
    record = await fleet.create_agent(user_id, name, image, False)
    return {"id": str(record["id"]), "name": record["name"], "status": record["status"]}


async def mcp_update_agent_file(
    fleet: FleetApp, agent_id: UUID, path: str, content: str
) -> dict:
    record = await fleet.upsert_file(agent_id, path, content)
    return {"agent_id": str(record["agent_id"]), "path": record["path"]}


async def mcp_start_agent(fleet: FleetApp, agent_id: UUID) -> dict:
    record = await fleet.find_agent(agent_id)
    if not record:
        raise ValueError(f"Agent {agent_id} not found")
    await fleet.start_sandbox(agent_id)
    updated = await fleet.find_agent(agent_id)
    return {"id": str(updated["id"]), "status": updated["status"]}


async def mcp_stop_agent(fleet: FleetApp, agent_id: UUID) -> dict:
    record = await fleet.find_agent(agent_id)
    if not record:
        raise ValueError(f"Agent {agent_id} not found")
    await fleet.stop_sandbox(agent_id)
    updated = await fleet.find_agent(agent_id)
    return {"id": str(updated["id"]), "status": updated["status"]}


async def mcp_delete_agent(fleet: FleetApp, agent_id: UUID) -> dict:
    record = await fleet.find_agent(agent_id)
    if not record:
        raise ValueError(f"Agent {agent_id} not found")
    if record["is_admin"]:
        raise ValueError("Cannot delete the Admin agent")
    await fleet.delete_agent(agent_id)
    return {"deleted": str(agent_id)}


async def mcp_list_skills(library: LibraryApp, user_id: UUID) -> list[dict]:
    records = await library.list_by_user(user_id)
    return [
        {"id": str(r["id"]), "name": r["name"], "description": r["description"]}
        for r in records
    ]


async def mcp_create_skill(
    library: LibraryApp, user_id: UUID, name: str, description: str
) -> dict:
    record = await library.create(user_id, name, description)
    return {"id": str(record["id"]), "name": record["name"]}


async def mcp_attach_skill(
    integrations: IntegrationsApp, agent_id: UUID, skill_id: UUID
) -> dict:
    await integrations.attach_skill(agent_id, skill_id)
    return {"agent_id": str(agent_id), "skill_id": str(skill_id), "attached": True}


async def mcp_list_envs(integrations: IntegrationsApp, user_id: UUID) -> list[dict]:
    records = await integrations.list_envs(user_id)
    return [{"id": str(r["id"]), "name": r["name"]} for r in records]


async def mcp_create_env(
    integrations: IntegrationsApp, user_id: UUID, name: str, values_json: str
) -> dict:
    try:
        values = json.loads(values_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"values_json is not valid JSON: {exc}") from exc
    if not isinstance(values, dict):
        raise ValueError("values_json must be a JSON object ({KEY: VALUE} pairs)")
    record = await integrations.create_env(user_id, name, values)
    return {"id": str(record["id"]), "name": record["name"]}


async def mcp_list_channels(
    integrations: IntegrationsApp, user_id: UUID
) -> list[dict]:
    records = await integrations.list_channels(user_id)
    return [{"id": str(r["id"]), "type": r["type"]} for r in records]


# MCP tool wrappers (thin — validate auth, delegate to business logic)


@mcp.tool()
async def list_agents(context: Context) -> list[dict]:
    """List all agents for the authenticated user."""
    user_id = await _require_user(context)
    _assert_ready()
    assert _fleet is not None
    return await mcp_list_agents(_fleet, user_id)


@mcp.tool()
async def get_fleet_status(context: Context) -> dict:
    """Return all agents with a status summary (idle/running/error counts)."""
    user_id = await _require_user(context)
    _assert_ready()
    assert _fleet is not None
    return await mcp_get_fleet_status(_fleet, user_id)


@mcp.tool()
async def create_agent(
    context: Context, name: str, image: str = "ghcr.io/hkuds/nanobot:latest"
) -> dict:
    """Create a new agent. Returns {id, name, status}."""
    user_id = await _require_user(context)
    _assert_ready()
    assert _fleet is not None
    return await mcp_create_agent(_fleet, user_id, name, image)


@mcp.tool()
async def update_agent_file(
    context: Context, agent_id: str, path: str, content: str
) -> dict:
    """Upsert a workspace file for an agent."""
    await _require_user(context)
    _assert_ready()
    assert _fleet is not None
    return await mcp_update_agent_file(_fleet, UUID(agent_id), path, content)


@mcp.tool()
async def start_agent(context: Context, agent_id: str) -> dict:
    """Start an agent sandbox."""
    await _require_user(context)
    _assert_ready()
    assert _fleet is not None
    return await mcp_start_agent(_fleet, UUID(agent_id))


@mcp.tool()
async def stop_agent(context: Context, agent_id: str) -> dict:
    """Stop an agent sandbox."""
    await _require_user(context)
    _assert_ready()
    assert _fleet is not None
    return await mcp_stop_agent(_fleet, UUID(agent_id))


@mcp.tool()
async def delete_agent(context: Context, agent_id: str) -> dict:
    """Delete an agent. Raises if agent is the Admin agent."""
    await _require_user(context)
    _assert_ready()
    assert _fleet is not None
    return await mcp_delete_agent(_fleet, UUID(agent_id))


@mcp.tool()
async def list_skills(context: Context) -> list[dict]:
    """List all skills in the user's library."""
    user_id = await _require_user(context)
    _assert_ready()
    assert _library is not None
    return await mcp_list_skills(_library, user_id)


@mcp.tool()
async def create_skill(context: Context, name: str, description: str = "") -> dict:
    """Create a new skill in the user's library."""
    user_id = await _require_user(context)
    _assert_ready()
    assert _library is not None
    return await mcp_create_skill(_library, user_id, name, description)


@mcp.tool()
async def attach_skill(context: Context, agent_id: str, skill_id: str) -> dict:
    """Attach a skill to an agent."""
    await _require_user(context)
    _assert_ready()
    assert _integrations is not None
    return await mcp_attach_skill(_integrations, UUID(agent_id), UUID(skill_id))


@mcp.tool()
async def list_envs(context: Context) -> list[dict]:
    """List all env configs for the authenticated user (values never returned)."""
    user_id = await _require_user(context)
    _assert_ready()
    assert _integrations is not None
    return await mcp_list_envs(_integrations, user_id)


@mcp.tool()
async def create_env(context: Context, name: str, values_json: str) -> dict:
    """Create a named env config. values_json: JSON string of {KEY: VALUE} pairs."""
    user_id = await _require_user(context)
    _assert_ready()
    assert _integrations is not None
    return await mcp_create_env(_integrations, user_id, name, values_json)


@mcp.tool()
async def list_channels(context: Context) -> list[dict]:
    """List all channel integrations (config never returned)."""
    user_id = await _require_user(context)
    _assert_ready()
    assert _integrations is not None
    return await mcp_list_channels(_integrations, user_id)
