"""Cron tools — workspace-scoped schedule definitions and per-agent links.

Crons live in the workspace (one definition can fan out to many agents)
and are attached to an agent the same way every other resource is. The
attach link carries an `enabled` flag so an agent can pause its schedule
without deleting the cron or detaching it.
"""

import logging
from uuid import UUID

import src.entrypoint.mcp as _pkg
from fastmcp.server.context import Context

logger = logging.getLogger(__name__)

_KIND_VALUES = ("at", "every", "cron")


def _cron_summary(record: dict) -> dict:
    return {
        "id": str(record["id"]),
        "name": record["name"],
        "schedule_kind": record["schedule_kind"],
        "schedule_at_ms": record.get("schedule_at_ms"),
        "schedule_every_ms": record.get("schedule_every_ms"),
        "schedule_expr": record.get("schedule_expr"),
        "schedule_tz": record.get("schedule_tz"),
        "message": record["message"],
        "deliver": record["deliver"],
        "channel": record.get("channel"),
        "recipient": record.get("recipient"),
        "delete_after_run": record["delete_after_run"],
    }


@_pkg.admin_mcp.tool()
async def list_crons(context: Context) -> list[dict]:
    """List all cron definitions in the workspace."""
    workspace_id = await _pkg._require_workspace(context)
    _pkg._assert_ready()
    assert _pkg._integrations is not None
    records = await _pkg._integrations.list_crons(workspace_id)
    return [_cron_summary(r) for r in records]


@_pkg.admin_mcp.tool()
async def get_cron(context: Context, cron_id: str) -> dict:
    """Inspect a cron definition."""
    await _pkg._require_workspace(context)
    _pkg._assert_ready()
    assert _pkg._integrations is not None
    record = await _pkg._integrations.find_cron(UUID(cron_id))
    if not record:
        raise ValueError(f"Cron {cron_id} not found")
    return _cron_summary(record)


@_pkg.admin_mcp.tool()
async def create_cron(
    context: Context,
    name: str,
    schedule_kind: str,
    message: str,
    schedule_at_ms: int | None = None,
    schedule_every_ms: int | None = None,
    schedule_expr: str | None = None,
    schedule_tz: str | None = None,
    deliver: bool = False,
    channel: str | None = None,
    recipient: str | None = None,
    delete_after_run: bool = False,
) -> dict:
    """Create a workspace-scoped cron definition. Attach it to an agent
    afterwards with `attach_cron` — without an attach link the cron
    is dormant.

    schedule_kind:
      "at"    — single fire at `schedule_at_ms` (UNIX ms)
      "every" — every `schedule_every_ms` ms (>=1000)
      "cron"  — POSIX-cron `schedule_expr` (e.g. "0 9 * * *"); pair with
                `schedule_tz` (e.g. "Europe/Berlin") to anchor wall-clock time

    `message` is the text the agent will receive when the cron fires.
    Set `deliver=true` plus `channel`/`recipient` to also push the message
    out through a named channel (Slack/Telegram/etc.). Use
    `delete_after_run=true` for one-shot reminders.
    """
    if schedule_kind not in _KIND_VALUES:
        raise ValueError(f"schedule_kind must be one of {_KIND_VALUES}")
    workspace_id = await _pkg._require_workspace(context)
    _pkg._assert_ready()
    assert _pkg._integrations is not None
    record = await _pkg._integrations.create_cron(
        workspace_id,
        name,
        schedule_kind,
        schedule_at_ms,
        schedule_every_ms,
        schedule_expr,
        schedule_tz,
        message,
        deliver,
        channel,
        recipient,
        delete_after_run,
    )
    return _cron_summary(record)


@_pkg.admin_mcp.tool()
async def update_cron(
    context: Context,
    cron_id: str,
    name: str | None = None,
    schedule_kind: str | None = None,
    schedule_at_ms: int | None = None,
    schedule_every_ms: int | None = None,
    schedule_expr: str | None = None,
    schedule_tz: str | None = None,
    message: str | None = None,
    deliver: bool | None = None,
    channel: str | None = None,
    recipient: str | None = None,
    delete_after_run: bool | None = None,
) -> dict:
    """Update a cron definition. Only fields you pass are changed."""
    if schedule_kind is not None and schedule_kind not in _KIND_VALUES:
        raise ValueError(f"schedule_kind must be one of {_KIND_VALUES}")
    await _pkg._require_workspace(context)
    _pkg._assert_ready()
    assert _pkg._integrations is not None
    fields: dict = {}
    if name is not None:
        fields["name"] = name
    if schedule_kind is not None:
        fields["schedule_kind"] = schedule_kind
    if schedule_at_ms is not None:
        fields["schedule_at_ms"] = schedule_at_ms
    if schedule_every_ms is not None:
        fields["schedule_every_ms"] = schedule_every_ms
    if schedule_expr is not None:
        fields["schedule_expr"] = schedule_expr
    if schedule_tz is not None:
        fields["schedule_tz"] = schedule_tz
    if message is not None:
        fields["message"] = message
    if deliver is not None:
        fields["deliver"] = deliver
    if channel is not None:
        fields["channel"] = channel
    if recipient is not None:
        fields["recipient"] = recipient
    if delete_after_run is not None:
        fields["delete_after_run"] = delete_after_run
    if not fields:
        raise ValueError("At least one field must be provided")
    record = await _pkg._integrations.update_cron(UUID(cron_id), **fields)
    if not record:
        raise ValueError(f"Cron {cron_id} not found")
    return _cron_summary(record)


@_pkg.admin_mcp.tool()
async def delete_cron(context: Context, cron_id: str) -> dict:
    """Permanently delete a cron definition. Cascades to every agent it
    was attached to. Confirm with the user — irreversible."""
    await _pkg._require_workspace(context)
    _pkg._assert_ready()
    assert _pkg._integrations is not None
    await _pkg._integrations.delete_cron(UUID(cron_id))
    return {"deleted": cron_id}


@_pkg.admin_mcp.tool()
async def attach_cron(
    context: Context, agent_id: str, cron_id: str, enabled: bool = True
) -> dict:
    """Attach a cron to an agent. Set `enabled=false` to wire it up but keep
    it paused until the user is ready."""
    await _pkg._require_workspace(context)
    _pkg._assert_ready()
    assert _pkg._integrations is not None
    await _pkg._integrations.attach_cron(UUID(agent_id), UUID(cron_id), enabled)
    return {
        "agent_id": agent_id,
        "cron_id": cron_id,
        "enabled": enabled,
        "attached": True,
    }


@_pkg.admin_mcp.tool()
async def detach_cron(context: Context, agent_id: str, cron_id: str) -> dict:
    """Detach a cron from an agent. The cron definition itself is preserved."""
    await _pkg._require_workspace(context)
    _pkg._assert_ready()
    assert _pkg._integrations is not None
    await _pkg._integrations.detach_cron(UUID(agent_id), UUID(cron_id))
    return {"agent_id": agent_id, "cron_id": cron_id, "detached": True}


@_pkg.admin_mcp.tool()
async def set_cron_enabled(
    context: Context, agent_id: str, cron_id: str, enabled: bool
) -> dict:
    """Toggle a cron attachment on or off without detaching it. Useful for
    pausing a recurring schedule the user wants to revisit later."""
    await _pkg._require_workspace(context)
    _pkg._assert_ready()
    assert _pkg._integrations is not None
    record = await _pkg._integrations.set_agent_cron_enabled(
        UUID(agent_id), UUID(cron_id), enabled
    )
    if not record:
        raise ValueError(f"Cron {cron_id} is not attached to agent {agent_id}")
    return {"agent_id": agent_id, "cron_id": cron_id, "enabled": enabled}
