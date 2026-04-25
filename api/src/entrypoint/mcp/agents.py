"""Agent tools — fleet inspection, agent CRUD, and per-agent file edits."""

from uuid import UUID

import src.entrypoint.mcp as _pkg
from fastmcp.server.context import Context


@_pkg.admin_mcp.tool()
async def get_agent(context: Context, agent_id: str) -> dict:
    """Inspect a single agent — metadata, all workspace files, and every
    attached resource (skills, envs, channels, MCP servers, templates, crons)."""
    await _pkg._require_workspace(context)
    _pkg._assert_ready()
    assert _pkg._fleet is not None
    assert _pkg._integrations is not None
    record = await _pkg._fleet.find_agent(UUID(agent_id))
    if not record:
        raise ValueError(f"Agent {agent_id} not found")
    files = await _pkg._fleet.list_files(UUID(agent_id))
    skills = await _pkg._integrations.list_agent_skills(UUID(agent_id))
    envs = await _pkg._integrations.list_agent_envs(UUID(agent_id))
    channels = await _pkg._integrations.list_agent_channels(UUID(agent_id))
    mcps = await _pkg._integrations.list_agent_mcps(UUID(agent_id))
    templates = await _pkg._integrations.list_agent_templates(UUID(agent_id))
    crons = await _pkg._integrations.list_agent_crons(UUID(agent_id))
    return {
        "id": str(record["id"]),
        "name": record["name"],
        "status": record["status"],
        "is_admin": record["is_admin"],
        "image": record["image"],
        "heartbeat_enabled": record["heartbeat_enabled"],
        "heartbeat_interval_s": record["heartbeat_interval_s"],
        "files": [{"path": f["path"], "content": f["content"]} for f in files],
        "skills": [{"id": str(s["id"]), "name": s["name"]} for s in skills],
        "envs": [{"id": str(e["id"]), "name": e["name"]} for e in envs],
        "channels": [{"id": str(c["id"]), "type": c["type"]} for c in channels],
        "mcp_servers": [{"id": str(m["id"]), "name": m["name"]} for m in mcps],
        "templates": [
            {"id": str(t["id"]), "name": t["name"], "template_type": t["template_type"]}
            for t in templates
        ],
        "crons": [
            {"id": str(c["id"]), "name": c["name"], "enabled": c["enabled"]}
            for c in crons
        ],
    }


@_pkg.admin_mcp.tool()
async def list_fleet(context: Context) -> dict:
    """List every agent in the workspace with a status summary
    (idle / running / error counts). Use this for the bird's-eye view;
    call `get_agent` to drill into one."""
    workspace_id = await _pkg._require_workspace(context)
    _pkg._assert_ready()
    assert _pkg._fleet is not None
    records = await _pkg._fleet.list_agents(workspace_id)
    agents = [
        {
            "id": str(r["id"]),
            "name": r["name"],
            "status": r["status"],
            "is_admin": r["is_admin"],
            "image": r["image"],
        }
        for r in records
    ]
    summary: dict[str, int] = {}
    for a in agents:
        summary[a["status"]] = summary.get(a["status"], 0) + 1
    return {"agents": agents, "summary": summary}


@_pkg.admin_mcp.tool()
async def create_agent(
    context: Context,
    name: str,
    image: str = "localhost:5005/officeclaw/agent:latest",
) -> dict:
    """Create a new (non-admin) agent. Returns {id, name, status}.

    The agent is created in `idle` state with default heartbeat off and the
    workspace's default LLM + web-search envs auto-attached. Identity files
    (SOUL.md / AGENTS.md / USER.md) start empty — write them with
    `update_agent_file` once you have the agent's scope from the user.
    """
    workspace_id = await _pkg._require_workspace(context)
    _pkg._assert_ready()
    assert _pkg._fleet is not None
    record = await _pkg._fleet.create_agent(workspace_id, name, image, False)
    return {"id": str(record["id"]), "name": record["name"], "status": record["status"]}


@_pkg.admin_mcp.tool()
async def update_agent(
    context: Context,
    agent_id: str,
    name: str | None = None,
    image: str | None = None,
    skill_evolution: bool | None = None,
    heartbeat_enabled: bool | None = None,
    heartbeat_interval_s: int | None = None,
) -> dict:
    """Update agent settings. Only fields you pass are changed.

    `heartbeat_interval_s` is bounded to [60, 86400] (1 minute … 1 day).
    Toggle `heartbeat_enabled=true` for the agent to wake up periodically
    and act on `HEARTBEAT.md`.
    """
    await _pkg._require_workspace(context)
    _pkg._assert_ready()
    assert _pkg._fleet is not None
    fields: dict = {}
    if name is not None:
        fields["name"] = name
    if image is not None:
        fields["image"] = image
    if skill_evolution is not None:
        fields["skill_evolution"] = skill_evolution
    if heartbeat_enabled is not None:
        fields["heartbeat_enabled"] = heartbeat_enabled
    if heartbeat_interval_s is not None:
        if heartbeat_interval_s < 60 or heartbeat_interval_s > 86_400:
            raise ValueError("heartbeat_interval_s must be in [60, 86400]")
        fields["heartbeat_interval_s"] = heartbeat_interval_s
    if not fields:
        raise ValueError("At least one field must be provided")
    record = await _pkg._fleet.update_agent(UUID(agent_id), **fields)
    if not record:
        raise ValueError(f"Agent {agent_id} not found")
    return {
        "id": str(record["id"]),
        "name": record["name"],
        "status": record["status"],
        "image": record["image"],
        "heartbeat_enabled": record["heartbeat_enabled"],
        "heartbeat_interval_s": record["heartbeat_interval_s"],
    }


@_pkg.admin_mcp.tool()
async def delete_agent(context: Context, agent_id: str) -> dict:
    """Delete an agent and all its files / link rows. Refuses to delete
    the workspace's Admin agent — that one is bootstrap-managed."""
    await _pkg._require_workspace(context)
    _pkg._assert_ready()
    assert _pkg._fleet is not None
    record = await _pkg._fleet.find_agent(UUID(agent_id))
    if not record:
        raise ValueError(f"Agent {agent_id} not found")
    if record["is_admin"]:
        raise ValueError("Cannot delete the Admin agent")
    await _pkg._fleet.delete_agent(UUID(agent_id))
    return {"deleted": agent_id}


@_pkg.admin_mcp.tool()
async def update_agent_file(
    context: Context, agent_id: str, path: str, content: str
) -> dict:
    """Upsert a per-agent file (SOUL.md / AGENTS.md / USER.md / HEARTBEAT.md / TOOLS.md
    or any other path). Use this for agent-specific identity, instructions,
    or heartbeat task lists.

    For instructions you want to share across multiple agents, prefer
    `create_template` + `attach_template` — those compose at sandbox start
    so the per-agent file stays small.
    """
    await _pkg._require_workspace(context)
    _pkg._assert_ready()
    assert _pkg._fleet is not None
    record = await _pkg._fleet.upsert_file(UUID(agent_id), path, content)
    return {"agent_id": str(record["agent_id"]), "path": record["path"]}
