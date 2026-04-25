"""User MCP server tools — create MCP server configs and attach to agents."""

import json
from uuid import UUID

import src.entrypoint.mcp as _pkg
from fastmcp.server.context import Context


@_pkg.admin_mcp.tool()
async def list_mcp_servers(context: Context) -> list[dict]:
    """List all MCP server configs for the authenticated user."""
    workspace_id = await _pkg._require_workspace(context)
    _pkg._assert_ready()
    assert _pkg._integrations is not None
    records = await _pkg._integrations.list_mcps(workspace_id)
    return [{"id": str(r["id"]), "name": r["name"], "type": r["type"]} for r in records]


@_pkg.admin_mcp.tool()
async def create_mcp_server(
    context: Context, name: str, server_type: str, config_json: str
) -> dict:
    """Create a user MCP server config.

    server_type: "http" or "stdio"
    config_json: JSON string with transport config. Examples:
      http:  {"url": "https://...", "headers": {"Authorization": "Bearer ..."}}
      stdio: {"command": "npx", "args": ["-y", "@some/mcp-package"]}
    """
    workspace_id = await _pkg._require_workspace(context)
    _pkg._assert_ready()
    assert _pkg._integrations is not None
    try:
        config = json.loads(config_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"config_json is not valid JSON: {exc}") from exc
    if not isinstance(config, dict):
        raise ValueError("config_json must be a JSON object")
    record = await _pkg._integrations.create_mcp(workspace_id, name, server_type, config)
    return {"id": str(record["id"]), "name": record["name"], "type": record["type"]}


@_pkg.admin_mcp.tool()
async def update_mcp_server(
    context: Context,
    mcp_id: str,
    name: str | None = None,
    config_json: str | None = None,
) -> dict:
    """Update an MCP server config. Only fields you pass are changed.
    `config_json` (when provided) replaces the entire transport config."""
    await _pkg._require_workspace(context)
    _pkg._assert_ready()
    assert _pkg._integrations is not None
    config: dict | None = None
    if config_json is not None:
        try:
            parsed = json.loads(config_json)
        except json.JSONDecodeError as exc:
            raise ValueError(f"config_json is not valid JSON: {exc}") from exc
        if not isinstance(parsed, dict):
            raise ValueError("config_json must be a JSON object")
        config = parsed
    if name is None and config is None:
        raise ValueError("At least one field must be provided")
    record = await _pkg._integrations.update_mcp(
        UUID(mcp_id), name=name, config=config
    )
    if not record:
        raise ValueError(f"MCP server {mcp_id} not found")
    return {"id": str(record["id"]), "name": record["name"], "type": record["type"]}


@_pkg.admin_mcp.tool()
async def attach_mcp_server(context: Context, agent_id: str, mcp_id: str) -> dict:
    """Attach an MCP server config to an agent."""
    await _pkg._require_workspace(context)
    _pkg._assert_ready()
    assert _pkg._integrations is not None
    await _pkg._integrations.attach_mcp(UUID(agent_id), UUID(mcp_id))
    return {"agent_id": agent_id, "mcp_id": mcp_id, "attached": True}


@_pkg.admin_mcp.tool()
async def detach_mcp_server(context: Context, agent_id: str, mcp_id: str) -> dict:
    """Detach an MCP server from an agent. The config stays in the workspace."""
    await _pkg._require_workspace(context)
    _pkg._assert_ready()
    assert _pkg._integrations is not None
    await _pkg._integrations.detach_mcp(UUID(agent_id), UUID(mcp_id))
    return {"agent_id": agent_id, "mcp_id": mcp_id, "detached": True}


@_pkg.admin_mcp.tool()
async def delete_mcp_server(context: Context, mcp_id: str) -> dict:
    """Permanently delete an MCP server config. Cascades to every agent
    it was attached to. Confirm with the user — irreversible."""
    await _pkg._require_workspace(context)
    _pkg._assert_ready()
    assert _pkg._integrations is not None
    await _pkg._integrations.delete_mcp(UUID(mcp_id))
    return {"deleted": mcp_id}
