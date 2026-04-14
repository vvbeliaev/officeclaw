"""Channel integration tools — create channel configs and attach to agents."""

import json
from uuid import UUID

import src.entrypoint.mcp as _pkg
from fastmcp.server.context import Context


@_pkg.admin_mcp.tool()
async def list_channels(context: Context) -> list[dict]:
    """List all channel integrations (config never returned)."""
    workspace_id = await _pkg._require_workspace(context)
    _pkg._assert_ready()
    assert _pkg._integrations is not None
    records = await _pkg._integrations.list_channels(workspace_id)
    return [{"id": str(r["id"]), "name": r["name"], "type": r["type"]} for r in records]


@_pkg.admin_mcp.tool()
async def create_channel(
    context: Context, channel_type: str, config_json: str, name: str = ""
) -> dict:
    """Create a channel integration.

    channel_type: one of "telegram", "discord", "whatsapp"
    config_json: JSON string with channel-specific config. Examples:
      telegram: {"token": "123:ABC...", "allow_from": ["*"]}
      discord:  {"token": "..."}
      whatsapp: {"bridge_url": "ws://localhost:3001", "bridge_token": "..."}
    name: human-readable label for this channel (defaults to channel_type if omitted)
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
    effective_name = name.strip() or channel_type
    record = await _pkg._integrations.create_channel(workspace_id, effective_name, channel_type, config)
    return {"id": str(record["id"]), "name": record["name"], "type": record["type"]}


@_pkg.admin_mcp.tool()
async def attach_channel(context: Context, agent_id: str, channel_id: str) -> dict:
    """Attach a channel integration to an agent."""
    await _pkg._require_workspace(context)
    _pkg._assert_ready()
    assert _pkg._integrations is not None
    await _pkg._integrations.attach_channel(UUID(agent_id), UUID(channel_id))
    return {"agent_id": agent_id, "channel_id": channel_id, "attached": True}
