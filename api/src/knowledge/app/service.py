from uuid import UUID

from src.knowledge.core.ports.out import IKnowledgeStore


class KnowledgeService:
    def __init__(self, store: IKnowledgeStore) -> None:
        self._store = store

    async def ingest(self, user_id: UUID, text: str, metadata: dict) -> None:
        await self._store.ingest(user_id, text, metadata)

    async def query(self, user_id: UUID, query: str, mode: str = "hybrid") -> str:
        return await self._store.query(user_id, query, mode)

    async def get_graph(self, user_id: UUID) -> dict:
        return await self._store.get_graph(user_id)
