from __future__ import annotations

from urllib.parse import urlparse
from uuid import UUID

from lightrag import LightRAG, QueryParam
from lightrag.utils import EmbeddingFunc
from lightrag.llm.openai import openai_complete_if_cache, openai_embed

from src.shared.config import Settings


def _parse_pg_params(database_url: str) -> dict:
    """Parse DATABASE_URL into host/port/user/password/database dict."""
    p = urlparse(database_url)
    return {
        "host": p.hostname or "localhost",
        "port": str(p.port or 5432),
        "user": p.username or "postgres",
        "password": p.password or "",
        "database": p.path.lstrip("/"),
    }


class LightRAGStore:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._instances: dict[UUID, LightRAG] = {}
        self._pg = _parse_pg_params(settings.database_url)

    async def _get_or_create(self, user_id: UUID) -> LightRAG:
        if user_id not in self._instances:
            s = self._settings
            pg = self._pg

            async def llm_func(
                prompt: str,
                system_prompt: str | None = None,
                history_messages: list = [],
                **kwargs,
            ) -> str:
                return await openai_complete_if_cache(
                    model=s.knowledge_llm_model,
                    prompt=prompt,
                    system_prompt=system_prompt,
                    history_messages=history_messages,
                    api_key=s.knowledge_llm_api_key,
                    base_url=s.knowledge_llm_base_url,
                    **kwargs,
                )

            async def embed_func(texts: list[str]) -> list[list[float]]:
                return await openai_embed(
                    texts,
                    model=s.knowledge_embed_model,
                    api_key=s.knowledge_embed_api_key,
                    base_url=s.knowledge_embed_base_url,
                )

            rag = LightRAG(
                working_dir="data/kg",
                workspace=str(user_id),
                llm_model_func=llm_func,
                embedding_func=EmbeddingFunc(
                    embedding_dim=s.knowledge_embed_dim,
                    max_token_size=8192,
                    func=embed_func,
                ),
                kv_storage="PGKVStorage",
                vector_storage="PGVectorStorage",
                graph_storage="NetworkXStorage",
                doc_status_storage="PGDocStatusStorage",
                addon_params={
                    "host": pg["host"],
                    "port": int(pg["port"]),
                    "user": pg["user"],
                    "password": pg["password"],
                    "database": pg["database"],
                },
            )
            await rag.initialize()
            self._instances[user_id] = rag

        return self._instances[user_id]

    async def ingest(self, user_id: UUID, text: str, metadata: dict) -> None:
        rag = await self._get_or_create(user_id)
        await rag.ainsert(text)

    async def query(self, user_id: UUID, query: str, mode: str = "hybrid") -> str:
        rag = await self._get_or_create(user_id)
        result = await rag.aquery(query, param=QueryParam(mode=mode))
        return result if isinstance(result, str) else str(result)

    async def get_graph(self, user_id: UUID) -> dict:
        rag = await self._get_or_create(user_id)
        nx_graph = rag.chunk_entity_relation_graph._graph
        nodes = [
            {"id": node_id, **{k: str(v) for k, v in data.items()}}
            for node_id, data in nx_graph.nodes(data=True)
        ]
        edges = [
            {
                "source": src,
                "target": tgt,
                **{k: str(v) for k, v in data.items()},
            }
            for src, tgt, data in nx_graph.edges(data=True)
        ]
        return {"nodes": nodes, "edges": edges}
