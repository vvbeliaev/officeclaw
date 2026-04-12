"""Env config tools — create env configs and attach to agents."""

import json
from uuid import UUID

import src.entrypoint.mcp as _pkg
from fastmcp.server.context import Context


@_pkg.mcp.tool()
async def list_envs(context: Context) -> list[dict]:
    """List all env configs for the authenticated user (values never returned)."""
    user_id = await _pkg._require_user(context)
    _pkg._assert_ready()
    assert _pkg._integrations is not None
    records = await _pkg._integrations.list_envs(user_id)
    return [{"id": str(r["id"]), "name": r["name"]} for r in records]


@_pkg.mcp.tool()
async def create_env(context: Context, name: str, values_json: str) -> dict:
    """Create a named env config.

    values_json: JSON string of {KEY: VALUE} pairs.
    Example: '{"OPENAI_API_KEY": "sk-...", "SOME_OTHER_VAR": "value"}'
    """
    user_id = await _pkg._require_user(context)
    _pkg._assert_ready()
    assert _pkg._integrations is not None
    try:
        values = json.loads(values_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"values_json is not valid JSON: {exc}") from exc
    if not isinstance(values, dict):
        raise ValueError("values_json must be a JSON object ({KEY: VALUE} pairs)")
    record = await _pkg._integrations.create_env(user_id, name, values)
    return {"id": str(record["id"]), "name": record["name"]}


@_pkg.mcp.tool()
async def attach_env(context: Context, agent_id: str, env_id: str) -> dict:
    """Attach an env config to an agent."""
    await _pkg._require_user(context)
    _pkg._assert_ready()
    assert _pkg._integrations is not None
    await _pkg._integrations.attach_env(UUID(agent_id), UUID(env_id))
    return {"agent_id": agent_id, "env_id": env_id, "attached": True}
