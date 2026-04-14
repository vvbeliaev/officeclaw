"""Skill library tools — create skills, manage skill files, and attach to agents."""

from uuid import UUID

import src.entrypoint.mcp as _pkg
from fastmcp.server.context import Context

_SKILL_MD_TEMPLATE = """\
---
name: {name}
description: {description}
---

# {name}

{description}

## Overview

Describe what this skill provides and when to use it.

## Usage

Explain how to invoke the tools or use the resources in this skill.

## Files

List the files in this skill and what each one does.
"""


@_pkg.admin_mcp.tool()
async def get_skill(context: Context, skill_id: str) -> dict:
    """Inspect a skill — metadata and all files with their content."""
    await _pkg._require_workspace(context)
    _pkg._assert_ready()
    assert _pkg._library is not None
    record = await _pkg._library.find_by_id(UUID(skill_id))
    if not record:
        raise ValueError(f"Skill {skill_id} not found")
    files = await _pkg._library.list_files(UUID(skill_id))
    return {
        "id": str(record["id"]),
        "name": record["name"],
        "description": record["description"],
        "files": [{"path": f["path"], "content": f["content"]} for f in files],
    }


@_pkg.admin_mcp.tool()
async def list_skills(context: Context) -> list[dict]:
    """List all skills in the user's library."""
    workspace_id = await _pkg._require_workspace(context)
    _pkg._assert_ready()
    assert _pkg._library is not None
    records = await _pkg._library.list_by_user(workspace_id)
    return [
        {"id": str(r["id"]), "name": r["name"], "description": r["description"]}
        for r in records
    ]


@_pkg.admin_mcp.tool()
async def create_skill(context: Context, name: str, description: str = "") -> dict:
    """Create a new skill in the user's library.

    A default SKILL.md is created automatically — edit it with add_skill_file
    to document what the skill provides and how to use it.
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

    Use SKILL.md as the main documentation file for the skill.
    Other files (scripts, configs, markdown guides) can be added at any path —
    they will be available to the agent at skills/{skill_name}/{path}.
    """
    await _pkg._require_workspace(context)
    _pkg._assert_ready()
    assert _pkg._library is not None
    record = await _pkg._library.upsert_file(UUID(skill_id), path, content)
    return {"skill_id": skill_id, "path": record["path"]}


@_pkg.admin_mcp.tool()
async def attach_skill(context: Context, agent_id: str, skill_id: str) -> dict:
    """Attach a skill to an agent."""
    await _pkg._require_workspace(context)
    _pkg._assert_ready()
    assert _pkg._integrations is not None
    await _pkg._integrations.attach_skill(UUID(agent_id), UUID(skill_id))
    return {"agent_id": agent_id, "skill_id": skill_id, "attached": True}
