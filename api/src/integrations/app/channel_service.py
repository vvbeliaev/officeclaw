from uuid import UUID

import asyncpg

from src.integrations.adapters.out.channel_repo import ChannelRepo


class ChannelService:
    def __init__(self, repo: ChannelRepo) -> None:
        self._repo = repo

    async def create(self, user_id: UUID, type_: str, config: dict) -> asyncpg.Record:
        return await self._repo.create(user_id, type_, config)

    async def find(self, channel_id: UUID) -> asyncpg.Record | None:
        return await self._repo.find_by_id(channel_id)

    async def list(self, user_id: UUID) -> list[asyncpg.Record]:
        return await self._repo.list_by_user(user_id)

    async def get_decrypted(self, channel_id: UUID) -> dict:
        return await self._repo.get_decrypted_config(channel_id)

    async def delete(self, channel_id: UUID) -> None:
        await self._repo.delete(channel_id)
