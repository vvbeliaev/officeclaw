"""User template tools — create templates and attach to agents."""

from uuid import UUID

import src.entrypoint.mcp as _pkg
from fastmcp.server.context import Context

_TEMPLATE_TYPES = ("user", "soul", "agents", "heartbeat", "tools")


@_pkg.admin_mcp.tool()
async def get_template(context: Context, template_id: str) -> dict:
    """Inspect a template — returns full content."""
    await _pkg._require_workspace(context)
    _pkg._assert_ready()
    assert _pkg._integrations is not None
    record = await _pkg._integrations.find_template(UUID(template_id))
    if not record:
        raise ValueError(f"Template {template_id} not found")
    return {
        "id": str(record["id"]),
        "name": record["name"],
        "template_type": record["template_type"],
        "content": record["content"],
    }


@_pkg.admin_mcp.tool()
async def list_templates(context: Context) -> list[dict]:
    """List all user templates."""
    workspace_id = await _pkg._require_workspace(context)
    _pkg._assert_ready()
    assert _pkg._integrations is not None
    records = await _pkg._integrations.list_templates(workspace_id)
    return [
        {"id": str(r["id"]), "name": r["name"], "template_type": r["template_type"]}
        for r in records
    ]


@_pkg.admin_mcp.tool()
async def create_template(
    context: Context, name: str, template_type: str, content: str
) -> dict:
    """Create a user template.

    template_type: one of "user", "soul", "agents", "heartbeat", "tools"

    Templates are prepended to the matching nanobot runtime file (e.g. SOUL.md)
    when an agent sandbox starts. Use them for shared base instructions that
    apply across multiple agents — the agent-specific override (if any) is
    appended after a "---" separator.
    """
    if template_type not in _TEMPLATE_TYPES:
        raise ValueError(
            f"template_type must be one of {_TEMPLATE_TYPES}, got {template_type!r}"
        )
    workspace_id = await _pkg._require_workspace(context)
    _pkg._assert_ready()
    assert _pkg._integrations is not None
    record = await _pkg._integrations.create_template(workspace_id, name, template_type, content)
    return {
        "id": str(record["id"]),
        "name": record["name"],
        "template_type": record["template_type"],
    }


@_pkg.admin_mcp.tool()
async def update_template(
    context: Context,
    template_id: str,
    name: str | None = None,
    content: str | None = None,
) -> dict:
    """Update a template. Only fields you pass are changed. `template_type`
    is immutable — create a new template if you need to switch slot."""
    await _pkg._require_workspace(context)
    _pkg._assert_ready()
    assert _pkg._integrations is not None
    if name is None and content is None:
        raise ValueError("At least one field must be provided")
    record = await _pkg._integrations.update_template(
        UUID(template_id), name=name, content=content
    )
    if not record:
        raise ValueError(f"Template {template_id} not found")
    return {
        "id": str(record["id"]),
        "name": record["name"],
        "template_type": record["template_type"],
    }


@_pkg.admin_mcp.tool()
async def attach_template(context: Context, agent_id: str, template_id: str) -> dict:
    """Attach a user template to an agent.

    The template_type is read from the template record automatically.
    At sandbox start the template content is prepended to the matching
    runtime file (SOUL.md, AGENTS.md, HEARTBEAT.md, TOOLS.md, or USER.md).
    """
    await _pkg._require_workspace(context)
    _pkg._assert_ready()
    assert _pkg._integrations is not None
    template = await _pkg._integrations.find_template(UUID(template_id))
    if not template:
        raise ValueError(f"Template {template_id} not found")
    await _pkg._integrations.attach_template(
        UUID(agent_id), UUID(template_id), template["template_type"]
    )
    return {"agent_id": agent_id, "template_id": template_id, "attached": True}


@_pkg.admin_mcp.tool()
async def detach_template(context: Context, agent_id: str, template_id: str) -> dict:
    """Detach a template from an agent. The template stays in the workspace
    and can be re-attached or attached to other agents."""
    await _pkg._require_workspace(context)
    _pkg._assert_ready()
    assert _pkg._integrations is not None
    await _pkg._integrations.detach_template(UUID(agent_id), UUID(template_id))
    return {"agent_id": agent_id, "template_id": template_id, "detached": True}


@_pkg.admin_mcp.tool()
async def delete_template(context: Context, template_id: str) -> dict:
    """Permanently delete a template. Cascades to every agent it was
    attached to. Confirm with the user — irreversible."""
    await _pkg._require_workspace(context)
    _pkg._assert_ready()
    assert _pkg._integrations is not None
    await _pkg._integrations.delete_template(UUID(template_id))
    return {"deleted": template_id}
