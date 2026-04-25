"""Seed-skill loader for new workspaces.

Walks the on-disk seed-skills tree and provisions each skill into a
freshly created workspace via LibraryApp. Skills whose frontmatter
declares `metadata.officeclaw.default_attach_to_admin: true` are
attached to the Admin agent so the user gets them out of the box.

Source-of-truth lives at:
    api/src/workspace/seed_skills/<slug>/{SKILL.md, ...}

Each subdirectory becomes one skill row. The loader is idempotent on
(workspace_id, skill_name): re-running it for an existing workspace
will skip skills already present, which lets us call it from a
backfill script in the future without double-seeding.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from uuid import UUID

from src.library.app.frontmatter import Frontmatter, parse as parse_frontmatter

if TYPE_CHECKING:
    from src.integrations.app import IntegrationsApp
    from src.library.app import LibraryApp

SEED_DIR: Path = Path(__file__).resolve().parent.parent / "seed_skills"


async def seed_workspace_skills(
    workspace_id: UUID,
    admin_agent_id: UUID,
    library: LibraryApp,
    integrations: IntegrationsApp,
) -> list[dict]:
    """Provision every seed skill into `workspace_id`.

    Returns the list of skill records created (skips already-present
    ones). Attaches skills marked `default_attach_to_admin` to the
    Admin agent.
    """
    if not SEED_DIR.is_dir():
        return []

    existing = {s["name"] for s in await library.list_by_workspace(workspace_id)}
    created: list[dict] = []

    for skill_dir in sorted(p for p in SEED_DIR.iterdir() if p.is_dir()):
        skill_md_path = skill_dir / "SKILL.md"
        if not skill_md_path.is_file():
            continue

        raw = skill_md_path.read_text(encoding="utf-8")
        fm, _body = parse_frontmatter(raw)
        skill_name = fm.name or skill_dir.name
        if skill_name in existing:
            continue

        record = await library.create(
            workspace_id,
            skill_name,
            fm.description or "",
            always=fm.always,
            emoji=fm.emoji,
            homepage=fm.homepage,
            required_bins=list(fm.required_bins),
            required_envs=list(fm.required_envs),
            metadata_extra=fm.metadata_extra,
        )
        skill_id = record["id"]

        for file_path in sorted(skill_dir.rglob("*")):
            if not file_path.is_file():
                continue
            rel = file_path.relative_to(skill_dir).as_posix()
            content = file_path.read_text(encoding="utf-8")
            await library.upsert_file(skill_id, rel, content)

        if _is_default_attach_to_admin(fm):
            await integrations.attach_skill(admin_agent_id, skill_id)

        created.append(record)

    return created


def _is_default_attach_to_admin(fm: Frontmatter) -> bool:
    officeclaw_meta = fm.metadata_extra.get("officeclaw")
    return isinstance(officeclaw_meta, dict) and bool(
        officeclaw_meta.get("default_attach_to_admin")
    )


__all__ = ["seed_workspace_skills", "SEED_DIR"]
