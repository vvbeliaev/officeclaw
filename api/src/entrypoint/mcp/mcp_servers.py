"""User MCP server tools — create MCP server configs and attach to agents."""

import json
from uuid import UUID

import src.entrypoint.mcp as _pkg
from fastmcp.server.context import Context


@_pkg.mcp.tool()
async def list_mcp_servers(context: Context) -> list[dict]:
    """List all MCP server configs for the authenticated user."""
    user_id = await _pkg._require_user(context)
    _pkg._assert_ready()
    assert _pkg._integrations is not None
    records = await _pkg._integrations.list_mcps(user_id)
    return [{"id": str(r["id"]), "name": r["name"], "type": r["type"]} for r in records]


@_pkg.mcp.tool()
async def create_mcp_server(
    context: Context, name: str, server_type: str, config_json: str
) -> dict:
    """Create a user MCP server config.

    server_type: "http" or "stdio"
    config_json: JSON string with transport config. Examples:
      http:  {"url": "https://...", "headers": {"Authorization": "Bearer ..."}}
      stdio: {"command": "npx", "args": ["-y", "@some/mcp-package"]}
    """
    user_id = await _pkg._require_user(context)
    _pkg._assert_ready()
    assert _pkg._integrations is not None
    try:
        config = json.loads(config_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"config_json is not valid JSON: {exc}") from exc
    if not isinstance(config, dict):
        raise ValueError("config_json must be a JSON object")
    record = await _pkg._integrations.create_mcp(user_id, name, server_type, config)
    return {"id": str(record["id"]), "name": record["name"], "type": record["type"]}


@_pkg.mcp.tool()
async def attach_mcp_server(context: Context, agent_id: str, mcp_id: str) -> dict:
    """Attach an MCP server config to an agent."""
    await _pkg._require_user(context)
    _pkg._assert_ready()
    assert _pkg._integrations is not None
    await _pkg._integrations.attach_mcp(UUID(agent_id), UUID(mcp_id))
    return {"agent_id": agent_id, "mcp_id": mcp_id, "attached": True}
