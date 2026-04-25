"""Skill library tools — create skills, manage skill files, and attach to agents."""

import logging
from uuid import UUID

import src.entrypoint.mcp as _pkg
from fastmcp.server.context import Context
from src.library.app import ClawhubImportError

logger = logging.getLogger(__name__)

# Body-only template. Structured fields (name / description / always /
# emoji / homepage / requires) live in DB columns and get synthesized
# into a `---` block at sandbox assembly — so we don't write a
# frontmatter block here.
_SKILL_MD_TEMPLATE = """\
# {name}

{description}

## Overview

Describe what this skill provides and when to use it.

## Usage

Explain how to invoke the tools or use the resources in this skill.

## Files

List the files in this skill and what each one does.
"""


def _skill_summary(record: dict) -> dict:
    return {
        "id": str(record["id"]),
        "name": record["name"],
        "description": record["description"],
        "always": record["always"],
        "emoji": record["emoji"],
        "homepage": record["homepage"],
        "required_bins": list(record["required_bins"] or ()),
        "required_envs": list(record["required_envs"] or ()),
    }


@_pkg.admin_mcp.tool()
async def get_skill(context: Context, skill_id: str) -> dict:
    """Inspect a skill — metadata, files, and all structured fields."""
    await _pkg._require_workspace(context)
    _pkg._assert_ready()
    assert _pkg._library is not None
    record = await _pkg._library.find_by_id(UUID(skill_id))
    if not record:
        raise ValueError(f"Skill {skill_id} not found")
    files = await _pkg._library.list_files(UUID(skill_id))
    return {
        **_skill_summary(record),
        "files": [{"path": f["path"], "content": f["content"]} for f in files],
    }


@_pkg.admin_mcp.tool()
async def list_skills(context: Context) -> list[dict]:
    """List all skills in the workspace."""
    workspace_id = await _pkg._require_workspace(context)
    _pkg._assert_ready()
    assert _pkg._library is not None
    records = await _pkg._library.list_by_workspace(workspace_id)
    return [_skill_summary(r) for r in records]


@_pkg.admin_mcp.tool()
async def create_skill(context: Context, name: str, description: str = "") -> dict:
    """Create a new skill in the workspace.

    A default SKILL.md body is seeded automatically — edit it with
    `add_skill_file`, and use `set_skill_metadata` to toggle `always`,
    set `emoji`, declare required bins / envs, etc.
    """
    workspace_id = await _pkg._require_workspace(context)
    _pkg._assert_ready()
    assert _pkg._library is not None
    record = await _pkg._library.create(workspace_id, name, description)
    skill_id = record["id"]
    default_doc = _SKILL_MD_TEMPLATE.format(
        name=name,
        description=description or "No description provided.",
    )
    await _pkg._library.upsert_file(skill_id, "SKILL.md", default_doc)
    return {"id": str(skill_id), "name": record["name"]}


@_pkg.admin_mcp.tool()
async def add_skill_file(
    context: Context, skill_id: str, path: str, content: str
) -> dict:
    """Add or update a file in a skill.

    When `path` is `SKILL.md`, any `---`-delimited frontmatter block at
    the top is parsed and absorbed into the skill's structured fields;
    the stored body is frontmatter-free. For other paths the content
    is stored verbatim and exposed to the agent at
    `skills/{skill_name}/{path}` inside the sandbox.
    """
    await _pkg._require_workspace(context)
    _pkg._assert_ready()
    assert _pkg._library is not None
    record = await _pkg._library.upsert_file(UUID(skill_id), path, content)
    return {"skill_id": skill_id, "path": record["path"]}


@_pkg.admin_mcp.tool()
async def set_skill_metadata(
    context: Context,
    skill_id: str,
    name: str | None = None,
    description: str | None = None,
    always: bool | None = None,
    emoji: str | None = None,
    homepage: str | None = None,
    required_bins: list[str] | None = None,
    required_envs: list[str] | None = None,
) -> dict:
    """Update structured metadata on a skill.

    Only fields you pass are changed; omit a field to leave it alone.
    Toggle `always=true` to force nanobot to keep the skill pinned in
    the system prompt instead of surfacing it via progressive disclosure.
    """
    await _pkg._require_workspace(context)
    _pkg._assert_ready()
    assert _pkg._library is not None
    fields: dict = {}
    if name is not None:
        fields["name"] = name
    if description is not None:
        fields["description"] = description
    if always is not None:
        fields["always"] = always
    if emoji is not None:
        fields["emoji"] = emoji
    if homepage is not None:
        fields["homepage"] = homepage
    if required_bins is not None:
        fields["required_bins"] = required_bins
    if required_envs is not None:
        fields["required_envs"] = required_envs
    if not fields:
        raise ValueError("At least one field must be provided")
    record = await _pkg._library.update(UUID(skill_id), **fields)
    if not record:
        raise ValueError(f"Skill {skill_id} not found")
    return _skill_summary(record)


@_pkg.admin_mcp.tool()
async def attach_skill(context: Context, agent_id: str, skill_id: str) -> dict:
    """Attach a skill to an agent."""
    await _pkg._require_workspace(context)
    _pkg._assert_ready()
    assert _pkg._integrations is not None
    await _pkg._integrations.attach_skill(UUID(agent_id), UUID(skill_id))
    return {"agent_id": agent_id, "skill_id": skill_id, "attached": True}


@_pkg.admin_mcp.tool()
async def detach_skill(context: Context, agent_id: str, skill_id: str) -> dict:
    """Detach a skill from an agent. The skill itself stays in the workspace
    library and remains attachable to other agents."""
    await _pkg._require_workspace(context)
    _pkg._assert_ready()
    assert _pkg._integrations is not None
    await _pkg._integrations.detach_skill(UUID(agent_id), UUID(skill_id))
    return {"agent_id": agent_id, "skill_id": skill_id, "detached": True}


@_pkg.admin_mcp.tool()
async def delete_skill(context: Context, skill_id: str) -> dict:
    """Permanently delete a skill from the workspace library.

    This cascades to every agent: the skill becomes detached from all of
    them, and its files are removed. Confirm with the user before calling —
    the operation is irreversible.
    """
    await _pkg._require_workspace(context)
    _pkg._assert_ready()
    assert _pkg._library is not None
    await _pkg._library.delete(UUID(skill_id))
    return {"deleted": skill_id}


@_pkg.admin_mcp.tool()
async def import_skill_from_clawhub(context: Context, url: str) -> dict:
    """Import a skill from clawhub.ai into the workspace skill library.

    `url` must look like `https://clawhub.ai/<owner>/<slug>`. The remote
    archive is fetched, validated, and unpacked server-side; SKILL.md
    frontmatter is absorbed into the skill row, and every other file
    is stored verbatim. The new skill is NOT auto-attached to any
    agent — call `attach_skill` afterwards if needed.
    """
    workspace_id = await _pkg._require_workspace(context)
    _pkg._assert_ready()
    assert _pkg._library is not None
    try:
        record = await _pkg._library.import_from_clawhub(workspace_id, url)
    except ClawhubImportError as exc:
        # User-facing message — surface verbatim.
        raise ValueError(str(exc)) from exc
    except Exception as exc:
        # Anything else is a server bug or upstream flake. Log the full
        # stack trace, but return a short, non-leaky message to the agent
        # so the FastMCP layer doesn't degrade to opaque `McpError`.
        logger.exception("import_skill_from_clawhub failed for %r", url)
        raise ValueError(
            f"ClawHub import failed ({type(exc).__name__}): {exc}. "
            "See API server logs for details."
        ) from exc
    return _skill_summary(record)
