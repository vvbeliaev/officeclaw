from __future__ import annotations

import asyncio
import os
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


def _export_pg_env(pg: dict) -> None:
    """Set POSTGRES_* env vars that LightRAG PG backends require."""
    os.environ.setdefault("POSTGRES_HOST", pg["host"])
    os.environ.setdefault("POSTGRES_PORT", pg["port"])
    os.environ.setdefault("POSTGRES_USER", pg["user"])
    os.environ.setdefault("POSTGRES_PASSWORD", pg["password"])
    os.environ.setdefault("POSTGRES_DATABASE", pg["database"])


class LightRAGStore:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._instances: dict[UUID, LightRAG] = {}
        self._locks: dict[UUID, asyncio.Lock] = {}
        self._pg = _parse_pg_params(settings.database_url)
        _export_pg_env(self._pg)

    def _get_lock(self, workspace_id: UUID) -> asyncio.Lock:
        if workspace_id not in self._locks:
            self._locks[workspace_id] = asyncio.Lock()
        return self._locks[workspace_id]

    async def _get_or_create(self, workspace_id: UUID) -> LightRAG:
        if workspace_id in self._instances:
            return self._instances[workspace_id]
        async with self._get_lock(workspace_id):
            if workspace_id not in self._instances:  # double-checked locking
                s = self._settings
                pg = self._pg

                async def llm_func(
                    prompt: str,
                    system_prompt: str | None = None,
                    history_messages: list | None = None,
                    **kwargs,
                ) -> str:
                    return await openai_complete_if_cache(
                        model=s.knowledge_llm_model,
                        prompt=prompt,
                        system_prompt=system_prompt,
                        history_messages=history_messages or [],
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
                    workspace=str(workspace_id),
                    llm_model_func=llm_func,
                    embedding_func=EmbeddingFunc(
                        embedding_dim=s.knowledge_embed_dim,
                        max_token_size=8192,
                        func=embed_func,
                    ),
                    kv_storage="PGKVStorage",
                    vector_storage="PGVectorStorage",
                    graph_storage="PGGraphStorage",
                    doc_status_storage="PGDocStatusStorage",
                    addon_params={
                        "host": pg["host"],
                        "port": int(pg["port"]),
                        "user": pg["user"],
                        "password": pg["password"],
                        "database": pg["database"],
                    },
                )
                await rag.initialize_storages()
                self._instances[workspace_id] = rag
        return self._instances[workspace_id]

    async def ingest(self, workspace_id: UUID, text: str, metadata: dict) -> None:
        rag = await self._get_or_create(workspace_id)
        await rag.ainsert(text)

    async def query(self, workspace_id: UUID, query: str, mode: str = "hybrid") -> str:
        rag = await self._get_or_create(workspace_id)
        result = await rag.aquery(query, param=QueryParam(mode=mode))
        return result if isinstance(result, str) else str(result)

    async def get_graph(self, workspace_id: UUID) -> dict:
        rag = await self._get_or_create(workspace_id)
        nodes = await rag.chunk_entity_relation_graph.get_all_nodes()
        edges = await rag.chunk_entity_relation_graph.get_all_edges()
        return {"nodes": nodes or [], "edges": edges or []}
