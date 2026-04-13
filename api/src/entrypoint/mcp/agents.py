"""Agent tools — fleet overview, agent inspection, and agent creation."""

from uuid import UUID

import src.entrypoint.mcp as _pkg
from fastmcp.server.context import Context


@_pkg.admin_mcp.tool()
async def get_agent(context: Context, agent_id: str) -> dict:
    """Inspect a single agent — metadata, all workspace files, and every
    attached resource (skills, envs, channels, MCP servers, templates)."""
    await _pkg._require_user(context)
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
    return {
        "id": str(record["id"]),
        "name": record["name"],
        "status": record["status"],
        "is_admin": record["is_admin"],
        "image": record["image"],
        "files": [{"path": f["path"], "content": f["content"]} for f in files],
        "skills": [{"id": str(s["id"]), "name": s["name"]} for s in skills],
        "envs": [{"id": str(e["id"]), "name": e["name"]} for e in envs],
        "channels": [{"id": str(c["id"]), "type": c["type"]} for c in channels],
        "mcp_servers": [{"id": str(m["id"]), "name": m["name"]} for m in mcps],
        "templates": [
            {"id": str(t["id"]), "name": t["name"], "template_type": t["template_type"]}
            for t in templates
        ],
    }


@_pkg.admin_mcp.tool()
async def get_fleet_status(context: Context) -> dict:
    """Return all agents with a status summary (idle/running/error counts)."""
    user_id = await _pkg._require_user(context)
    _pkg._assert_ready()
    assert _pkg._fleet is not None
    records = await _pkg._fleet.list_agents(user_id)
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
    """Create a new agent. Returns {id, name, status}."""
    user_id = await _pkg._require_user(context)
    _pkg._assert_ready()
    assert _pkg._fleet is not None
    record = await _pkg._fleet.create_agent(user_id, name, image, False)
    return {"id": str(record["id"]), "name": record["name"], "status": record["status"]}


# --- Sandbox lifecycle (disabled — managed via UI for now) ---

# @_pkg.mcp.tool()
# async def start_agent(context: Context, agent_id: str) -> dict:
#     """Start an agent sandbox."""
#     await _pkg._require_user(context)
#     _pkg._assert_ready()
#     assert _pkg._fleet is not None
#     record = await _pkg._fleet.find_agent(UUID(agent_id))
#     if not record:
#         raise ValueError(f"Agent {agent_id} not found")
#     await _pkg._fleet.start_sandbox(UUID(agent_id))
#     updated = await _pkg._fleet.find_agent(UUID(agent_id))
#     return {"id": str(updated["id"]), "status": updated["status"]}

# @_pkg.mcp.tool()
# async def stop_agent(context: Context, agent_id: str) -> dict:
#     """Stop an agent sandbox."""
#     await _pkg._require_user(context)
#     _pkg._assert_ready()
#     assert _pkg._fleet is not None
#     record = await _pkg._fleet.find_agent(UUID(agent_id))
#     if not record:
#         raise ValueError(f"Agent {agent_id} not found")
#     await _pkg._fleet.stop_sandbox(UUID(agent_id))
#     updated = await _pkg._fleet.find_agent(UUID(agent_id))
#     return {"id": str(updated["id"]), "status": updated["status"]}

# @_pkg.mcp.tool()
# async def delete_agent(context: Context, agent_id: str) -> dict:
#     """Delete an agent. Raises if agent is the Admin agent."""
#     await _pkg._require_user(context)
#     _pkg._assert_ready()
#     assert _pkg._fleet is not None
#     record = await _pkg._fleet.find_agent(UUID(agent_id))
#     if not record:
#         raise ValueError(f"Agent {agent_id} not found")
#     if record["is_admin"]:
#         raise ValueError("Cannot delete the Admin agent")
#     await _pkg._fleet.delete_agent(UUID(agent_id))
#     return {"deleted": agent_id}

# @_pkg.mcp.tool()
# async def update_agent_file(
#     context: Context, agent_id: str, path: str, content: str
# ) -> dict:
#     """Upsert a workspace file for an agent."""
#     await _pkg._require_user(context)
#     _pkg._assert_ready()
#     assert _pkg._fleet is not None
#     record = await _pkg._fleet.upsert_file(UUID(agent_id), path, content)
#     return {"agent_id": str(record["agent_id"]), "path": record["path"]}
