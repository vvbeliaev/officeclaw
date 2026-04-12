"""User template tools — create templates and attach to agents."""

from uuid import UUID

import src.entrypoint.mcp as _pkg
from fastmcp.server.context import Context

_TEMPLATE_TYPES = ("user", "soul", "agents", "heartbeat", "tools")


@_pkg.mcp.tool()
async def get_template(context: Context, template_id: str) -> dict:
    """Inspect a template — returns full content."""
    await _pkg._require_user(context)
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


@_pkg.mcp.tool()
async def list_templates(context: Context) -> list[dict]:
    """List all user templates."""
    user_id = await _pkg._require_user(context)
    _pkg._assert_ready()
    assert _pkg._integrations is not None
    records = await _pkg._integrations.list_templates(user_id)
    return [
        {"id": str(r["id"]), "name": r["name"], "template_type": r["template_type"]}
        for r in records
    ]


@_pkg.mcp.tool()
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
    user_id = await _pkg._require_user(context)
    _pkg._assert_ready()
    assert _pkg._integrations is not None
    record = await _pkg._integrations.create_template(user_id, name, template_type, content)
    return {
        "id": str(record["id"]),
        "name": record["name"],
        "template_type": record["template_type"],
    }


@_pkg.mcp.tool()
async def attach_template(context: Context, agent_id: str, template_id: str) -> dict:
    """Attach a user template to an agent.

    The template_type is read from the template record automatically.
    At sandbox start the template content is prepended to the matching
    runtime file (SOUL.md, AGENTS.md, HEARTBEAT.md, TOOLS.md, or USER.md).
    """
    await _pkg._require_user(context)
    _pkg._assert_ready()
    assert _pkg._integrations is not None
    template = await _pkg._integrations.find_template(UUID(template_id))
    if not template:
        raise ValueError(f"Template {template_id} not found")
    await _pkg._integrations.attach_template(
        UUID(agent_id), UUID(template_id), template["template_type"]
    )
    return {"agent_id": agent_id, "template_id": template_id, "attached": True}
