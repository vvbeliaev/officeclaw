"""Env config tools — create env configs and attach to agents."""

import json
from uuid import UUID

import src.entrypoint.mcp as _pkg
from fastmcp.server.context import Context


@_pkg.admin_mcp.tool()
async def list_envs(context: Context) -> list[dict]:
    """List all env configs for the authenticated user (values never returned)."""
    workspace_id = await _pkg._require_workspace(context)
    _pkg._assert_ready()
    assert _pkg._integrations is not None
    records = await _pkg._integrations.list_envs(workspace_id)
    return [{"id": str(r["id"]), "name": r["name"]} for r in records]


@_pkg.admin_mcp.tool()
async def create_env(context: Context, name: str, values_json: str) -> dict:
    """Create a named env config.

    values_json: JSON string of {KEY: VALUE} pairs.
    Example: '{"OPENAI_API_KEY": "sk-...", "SOME_OTHER_VAR": "value"}'
    """
    workspace_id = await _pkg._require_workspace(context)
    _pkg._assert_ready()
    assert _pkg._integrations is not None
    try:
        values = json.loads(values_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"values_json is not valid JSON: {exc}") from exc
    if not isinstance(values, dict):
        raise ValueError("values_json must be a JSON object ({KEY: VALUE} pairs)")
    record = await _pkg._integrations.create_env(workspace_id, name, values)
    return {"id": str(record["id"]), "name": record["name"]}


@_pkg.admin_mcp.tool()
async def update_env(
    context: Context,
    env_id: str,
    name: str | None = None,
    values_json: str | None = None,
    category: str | None = None,
) -> dict:
    """Update an env config. Only fields you pass are changed.

    `values_json` (when provided) replaces the entire {KEY: VALUE} bundle —
    we don't merge. To rotate one secret, fetch the agent attachments,
    decide what should remain, then post the full new map.
    """
    await _pkg._require_workspace(context)
    _pkg._assert_ready()
    assert _pkg._integrations is not None
    values: dict | None = None
    if values_json is not None:
        try:
            parsed = json.loads(values_json)
        except json.JSONDecodeError as exc:
            raise ValueError(f"values_json is not valid JSON: {exc}") from exc
        if not isinstance(parsed, dict):
            raise ValueError("values_json must be a JSON object ({KEY: VALUE} pairs)")
        values = parsed
    if name is None and values is None and category is None:
        raise ValueError("At least one field must be provided")
    record = await _pkg._integrations.update_env(
        UUID(env_id), name=name, values=values, category=category
    )
    if not record:
        raise ValueError(f"Env {env_id} not found")
    return {"id": str(record["id"]), "name": record["name"]}


@_pkg.admin_mcp.tool()
async def attach_env(context: Context, agent_id: str, env_id: str) -> dict:
    """Attach an env config to an agent."""
    await _pkg._require_workspace(context)
    _pkg._assert_ready()
    assert _pkg._integrations is not None
    await _pkg._integrations.attach_env(UUID(agent_id), UUID(env_id))
    return {"agent_id": agent_id, "env_id": env_id, "attached": True}


@_pkg.admin_mcp.tool()
async def detach_env(context: Context, agent_id: str, env_id: str) -> dict:
    """Detach an env config from an agent. The env stays in the workspace."""
    await _pkg._require_workspace(context)
    _pkg._assert_ready()
    assert _pkg._integrations is not None
    await _pkg._integrations.detach_env(UUID(agent_id), UUID(env_id))
    return {"agent_id": agent_id, "env_id": env_id, "detached": True}


@_pkg.admin_mcp.tool()
async def delete_env(context: Context, env_id: str) -> dict:
    """Permanently delete an env config. Cascades to every agent it was
    attached to. Confirm with the user — irreversible, and any running agent
    that depends on this env will lose access on next sandbox start."""
    await _pkg._require_workspace(context)
    _pkg._assert_ready()
    assert _pkg._integrations is not None
    await _pkg._integrations.delete_env(UUID(env_id))
    return {"deleted": env_id}
