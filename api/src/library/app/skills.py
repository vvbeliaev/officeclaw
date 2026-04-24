from typing import Any
from uuid import UUID

from src.library.adapters.out.repository import SkillFileRepo, SkillRepo
from src.library.app.clawhub import ClawhubImportError, fetch as fetch_clawhub
from src.library.app.frontmatter import Frontmatter, parse as parse_frontmatter


class SkillService:
    def __init__(self, skill_repo: SkillRepo, skill_file_repo: SkillFileRepo) -> None:
        self._skills = skill_repo
        self._files = skill_file_repo

    async def create(
        self,
        workspace_id: UUID,
        name: str,
        description: str,
        *,
        always: bool = False,
        emoji: str | None = None,
        homepage: str | None = None,
        required_bins: list[str] | None = None,
        required_envs: list[str] | None = None,
        metadata_extra: dict[str, Any] | None = None,
    ) -> dict:
        return await self._skills.create(
            workspace_id,
            name,
            description,
            always=always,
            emoji=emoji,
            homepage=homepage,
            required_bins=required_bins,
            required_envs=required_envs,
            metadata_extra=metadata_extra,
        )

    async def find_by_id(self, skill_id: UUID) -> dict | None:
        return await self._skills.find_by_id(skill_id)

    async def list_by_workspace(self, workspace_id: UUID) -> list[dict]:
        return await self._skills.list_by_workspace(workspace_id)

    async def update(
        self,
        skill_id: UUID,
        **fields: Any,
    ) -> dict | None:
        return await self._skills.update(skill_id, **fields)

    async def delete(self, skill_id: UUID) -> None:
        await self._skills.delete(skill_id)

    async def upsert_file(self, skill_id: UUID, path: str, content: str) -> dict:
        """Write a skill file. For SKILL.md, parse the incoming frontmatter,
        absorb known fields into the skills row, and store the body only.
        """
        if path == "SKILL.md":
            fm, body = parse_frontmatter(content)
            await self._absorb_frontmatter(skill_id, fm)
            content = body
        record = await self._files.upsert(skill_id, path, content)
        return dict(record)

    async def list_files(self, skill_id: UUID) -> list[dict]:
        records = await self._files.list_by_skill(skill_id)
        return [dict(r) for r in records]

    async def delete_file(self, skill_id: UUID, path: str) -> bool:
        return await self._files.delete(skill_id, path)

    async def import_from_clawhub(self, workspace_id: UUID, url: str) -> dict:
        """Import a skill from a ClawHub URL.

        Raises ClawhubImportError (422-friendly) on validation issues.
        """
        parsed = await fetch_clawhub(url)

        # Split SKILL.md out of the archive so we can absorb its
        # frontmatter into the new skill row, and store only the body.
        skill_md_body: str | None = None
        fm = Frontmatter()
        other_files: list[tuple[str, str]] = []
        for path, file_content in parsed.files:
            if path == "SKILL.md":
                fm, skill_md_body = parse_frontmatter(file_content)
            else:
                other_files.append((path, file_content))

        # ClawHub's JSON metadata wins for the display fields; frontmatter
        # fills in anything the JSON didn't carry.
        description = parsed.description or fm.description or ""
        homepage = fm.homepage

        record = await self._skills.create(
            workspace_id,
            parsed.name,
            description,
            always=fm.always,
            emoji=fm.emoji,
            homepage=homepage,
            required_bins=list(fm.required_bins),
            required_envs=list(fm.required_envs),
            metadata_extra=fm.metadata_extra,
        )
        skill_id = record["id"]

        if skill_md_body is not None:
            await self._files.upsert(skill_id, "SKILL.md", skill_md_body)
        for path, file_content in other_files:
            await self._files.upsert(skill_id, path, file_content)
        return record

    async def _absorb_frontmatter(self, skill_id: UUID, fm: Frontmatter) -> None:
        """Propagate parsed frontmatter fields into the skills row.

        Only fields that appeared in the frontmatter are updated — absent
        fields keep whatever value the UI / MCP tool already set on the
        skill. `name` is left alone here because renames should go through
        the dedicated PATCH endpoint to avoid surprise collisions.
        """
        updates: dict[str, Any] = {}
        if fm.description is not None:
            updates["description"] = fm.description
        if fm.homepage is not None:
            updates["homepage"] = fm.homepage
        if fm.emoji is not None:
            updates["emoji"] = fm.emoji
        if fm.always:
            updates["always"] = True
        if fm.required_bins:
            updates["required_bins"] = list(fm.required_bins)
        if fm.required_envs:
            updates["required_envs"] = list(fm.required_envs)
        if fm.metadata_extra:
            updates["metadata_extra"] = fm.metadata_extra
        if updates:
            await self._skills.update(skill_id, **updates)


__all__ = ["SkillService", "ClawhubImportError"]
