from typing import Any, Protocol
from uuid import UUID


class ISkillRepo(Protocol):
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
    ) -> dict: ...
    async def find_by_id(self, skill_id: UUID) -> dict | None: ...
    async def list_by_workspace(self, workspace_id: UUID) -> list[dict]: ...
    async def update(
        self,
        skill_id: UUID,
        *,
        name: str | None = None,
        description: str | None = None,
        always: bool | None = None,
        emoji: str | None = None,
        homepage: str | None = None,
        required_bins: list[str] | None = None,
        required_envs: list[str] | None = None,
        metadata_extra: dict[str, Any] | None = None,
    ) -> dict | None: ...
    async def delete(self, skill_id: UUID) -> None: ...


class ISkillFileRepo(Protocol):
    async def upsert(self, skill_id: UUID, path: str, content: str) -> dict: ...
    async def list_by_skill(self, skill_id: UUID) -> list[dict]: ...
    async def delete(self, skill_id: UUID, path: str) -> bool: ...
