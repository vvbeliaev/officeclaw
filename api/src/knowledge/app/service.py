from uuid import UUID

from src.knowledge.core.ports.out import IDocumentNormalizer, IKnowledgeStore


class KnowledgeService:
    def __init__(self, store: IKnowledgeStore, normalizer: IDocumentNormalizer) -> None:
        self._store = store
        self._normalizer = normalizer

    async def ingest(self, workspace_id: UUID, text: str, metadata: dict) -> None:
        await self._store.ingest(workspace_id, text, metadata)

    async def ingest_file(self, workspace_id: UUID, content: bytes, content_type: str, filename: str) -> None:
        text = await self._normalizer.normalize(content, content_type, filename)
        metadata = {"filename": filename, "content_type": content_type}
        await self._store.ingest(workspace_id, text, metadata)

    async def query(self, workspace_id: UUID, query: str, mode: str = "hybrid") -> str:
        return await self._store.query(workspace_id, query, mode)

    async def get_graph(self, workspace_id: UUID) -> dict:
        return await self._store.get_graph(workspace_id)
