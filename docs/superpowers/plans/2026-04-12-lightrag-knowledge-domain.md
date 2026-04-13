# LightRAG Knowledge Domain Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a shared per-user knowledge graph layer to OfficeClaw so agents can ingest research findings and query accumulated knowledge across the fleet.

**Architecture:** New `knowledge` hexagonal domain in `api/src/knowledge/`. LightRAG runs as an embedded library — one `LightRAG` instance per user, lazily created and cached in-process. Storage: NetworkX `.graphml` for the graph (file per user), PGKVStorage + PGVectorStorage + PGDocStatusStorage in the existing Postgres. Agents access via two new MCP tools; users access via REST endpoints.

**Tech Stack:** `lightrag-hku`, `openai` (for LLM/embed), NetworkX (bundled with lightrag), pgvector (already in `pgvector/pgvector:pg18` image).

---

## File Map

**Create:**

- `api/src/knowledge/__init__.py`
- `api/src/knowledge/core/__init__.py`
- `api/src/knowledge/core/schema.py`
- `api/src/knowledge/core/ports/__init__.py`
- `api/src/knowledge/core/ports/_in.py`
- `api/src/knowledge/core/ports/out.py`
- `api/src/knowledge/app/__init__.py`
- `api/src/knowledge/app/service.py`
- `api/src/knowledge/adapters/__init__.py`
- `api/src/knowledge/adapters/_in/__init__.py`
- `api/src/knowledge/adapters/_in/router.py`
- `api/src/knowledge/adapters/out/__init__.py`
- `api/src/knowledge/adapters/out/lightrag_store.py`
- `api/src/knowledge/di.py`
- `api/tests/__init__.py`
- `api/tests/knowledge/__init__.py`
- `api/tests/knowledge/test_service.py`

**Modify:**

- `api/pyproject.toml` — add `lightrag-hku`, `openai`
- `api/src/shared/config.py` — add `knowledge_*` settings
- `api/migrations/versions/001_initial_schema.sql` — add `vector` extension
- `api/src/entrypoint/main.py` — mount knowledge domain
- `api/src/entrypoint/mcp/knowledge.py` — add `ingest_knowledge`, `query_knowledge` tools
- `compose.local.yml` — add `kg_data` volume

---

## Task 1: Add Dependencies

**Files:**

- Modify: `api/pyproject.toml`

- [ ] **Step 1: Add lightrag-hku and openai to pyproject.toml**

```toml
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.32",
    "asyncpg>=0.30",
    "pydantic>=2.9",
    "pydantic-settings>=2.6",
    "alembic>=1.14",
    "cryptography>=43",
    "python-dotenv>=1.0",
    "fastmcp>=2.3",
    "python-multipart>=0.0.9",
    "lightrag-hku>=1.3",
    "openai>=1.0",
]
```

- [ ] **Step 2: Install**

```bash
cd api && pip install -e ".[dev]"
```

Expected: resolves and installs `lightrag_hku`, `openai`, `networkx`, and their transitive deps without conflicts.

- [ ] **Step 3: Commit**

```bash
git add api/pyproject.toml
git commit -m "chore: add lightrag-hku and openai dependencies"
```

---

## Task 2: pgvector Extension in Migration

**Files:**

- Modify: `api/migrations/versions/001_initial_schema.sql`

PGVectorStorage requires the `vector` extension. The `pgvector/pgvector:pg18` image has it available but it must be explicitly enabled.

- [ ] **Step 1: Add extension to migration**

Open `api/migrations/versions/001_initial_schema.sql`. After the existing `CREATE EXTENSION IF NOT EXISTS "pgcrypto";` line, add:

```sql
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS vector;
```

- [ ] **Step 2: Apply to local DB (if already migrated)**

```bash
cd api && psql $DATABASE_URL -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

Expected: `CREATE EXTENSION` or `NOTICE: extension "vector" already exists, skipping`

- [ ] **Step 3: Commit**

```bash
git add api/migrations/versions/001_initial_schema.sql
git commit -m "feat(knowledge): enable pgvector extension in migration"
```

---

## Task 3: Knowledge Core — Schema and Ports

**Files:**

- Create: `api/src/knowledge/__init__.py`
- Create: `api/src/knowledge/core/__init__.py`
- Create: `api/src/knowledge/core/schema.py`
- Create: `api/src/knowledge/core/ports/__init__.py`
- Create: `api/src/knowledge/core/ports/_in.py`
- Create: `api/src/knowledge/core/ports/out.py`

- [ ] **Step 1: Write the failing test (schema validation)**

Create `api/tests/__init__.py` (empty), `api/tests/knowledge/__init__.py` (empty), then:

`api/tests/knowledge/test_service.py`:

```python
import pytest
from uuid import UUID
from src.knowledge.core.schema import IngestTextRequest, QueryRequest, QueryResponse, GraphData


def test_ingest_request_defaults():
    req = IngestTextRequest(text="hello world")
    assert req.text == "hello world"
    assert req.metadata == {}


def test_query_request_defaults():
    req = QueryRequest(query="what is X?")
    assert req.mode == "hybrid"


def test_query_response():
    resp = QueryResponse(answer="X is Y")
    assert resp.answer == "X is Y"


def test_graph_data_empty():
    g = GraphData(nodes=[], edges=[])
    assert g.nodes == []
    assert g.edges == []
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd api && pytest tests/knowledge/test_service.py -v
```

Expected: `ImportError` — `src.knowledge.core.schema` not found.

- [ ] **Step 3: Create package init files**

`api/src/knowledge/__init__.py`: empty file
`api/src/knowledge/core/__init__.py`: empty file
`api/src/knowledge/core/ports/__init__.py`: empty file
`api/src/knowledge/adapters/__init__.py`: empty file
`api/src/knowledge/adapters/_in/__init__.py`: empty file
`api/src/knowledge/adapters/out/__init__.py`: empty file

- [ ] **Step 4: Create schema**

`api/src/knowledge/core/schema.py`:

```python
from pydantic import BaseModel


class IngestTextRequest(BaseModel):
    text: str
    metadata: dict = {}


class QueryRequest(BaseModel):
    query: str
    mode: str = "hybrid"  # local | global | hybrid | naive


class QueryResponse(BaseModel):
    answer: str


class GraphNode(BaseModel):
    id: str
    type: str = ""
    description: str = ""


class GraphEdge(BaseModel):
    source: str
    target: str
    label: str = ""
    weight: float = 1.0


class GraphData(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
```

- [ ] **Step 5: Create ports**

`api/src/knowledge/core/ports/_in.py`:

```python
"""Inbound port — what the app layer offers to in-adapters."""
from typing import Protocol
from uuid import UUID


class IKnowledgeApp(Protocol):
    async def ingest(self, user_id: UUID, text: str, metadata: dict) -> None: ...
    async def query(self, user_id: UUID, query: str, mode: str) -> str: ...
    async def get_graph(self, user_id: UUID) -> dict: ...
```

`api/src/knowledge/core/ports/out.py`:

```python
"""Outbound port — what the app layer requires from storage."""
from typing import Protocol
from uuid import UUID


class IKnowledgeStore(Protocol):
    async def ingest(self, user_id: UUID, text: str, metadata: dict) -> None: ...
    async def query(self, user_id: UUID, query: str, mode: str) -> str: ...
    async def get_graph(self, user_id: UUID) -> dict: ...
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
cd api && pytest tests/knowledge/test_service.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add api/src/knowledge/ api/tests/
git commit -m "feat(knowledge): add core schema and ports"
```

---

## Task 4: LightRAGStore — Outbound Adapter

**Files:**

- Create: `api/src/knowledge/adapters/out/lightrag_store.py`

This adapter wraps LightRAG as a library. One `LightRAG` instance per user, lazily created and cached. Each instance uses `workspace=str(user_id)` — this controls the subdirectory for NetworkX files (`data/kg/{user_id}/`) and the `workspace` column in PG tables.

- [ ] **Step 1: Write the failing test (LightRAGStore stub)**

Add to `api/tests/knowledge/test_service.py`:

```python
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from src.knowledge.adapters.out.lightrag_store import LightRAGStore


@pytest.fixture
def mock_settings():
    s = MagicMock()
    s.database_url = "postgresql://postgres:postgres@localhost:5434/postgres"
    s.knowledge_llm_api_key = "test-key"
    s.knowledge_llm_base_url = "https://api.openai.com/v1"
    s.knowledge_llm_model = "gpt-4o-mini"
    s.knowledge_embed_api_key = "test-key"
    s.knowledge_embed_base_url = "https://api.openai.com/v1"
    s.knowledge_embed_model = "text-embedding-3-small"
    s.knowledge_embed_dim = 1536
    return s


@pytest.mark.asyncio
async def test_store_caches_instances(mock_settings):
    store = LightRAGStore(mock_settings)
    user_id = uuid4()

    with patch("src.knowledge.adapters.out.lightrag_store.LightRAG") as MockRAG:
        mock_rag = AsyncMock()
        MockRAG.return_value = mock_rag

        rag1 = await store._get_or_create(user_id)
        rag2 = await store._get_or_create(user_id)

    assert rag1 is rag2
    assert MockRAG.call_count == 1
    mock_rag.initialize.assert_awaited_once()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd api && pytest tests/knowledge/test_service.py::test_store_caches_instances -v
```

Expected: `ImportError` — `LightRAGStore` not found.

- [ ] **Step 3: Implement LightRAGStore**

`api/src/knowledge/adapters/out/lightrag_store.py`:

```python
from __future__ import annotations

import json
from urllib.parse import urlparse
from uuid import UUID

from lightrag import LightRAG, QueryParam
from lightrag.utils import EmbeddingFunc
from lightrag.llm.openai import openai_complete_if_cache, openai_embed

from src.shared.config import Settings


def _parse_pg_params(database_url: str) -> dict:
    """Parse DATABASE_URL into kwargs for LightRAG PG storage env vars."""
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
        # NetworkXStorage stores the graph at rag.chunk_entity_relation_graph._graph
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
```

- [ ] **Step 4: Run tests**

```bash
cd api && pytest tests/knowledge/test_service.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add api/src/knowledge/adapters/out/lightrag_store.py
git commit -m "feat(knowledge): add LightRAGStore outbound adapter"
```

---

## Task 5: App Layer — KnowledgeService and KnowledgeApp

**Files:**

- Create: `api/src/knowledge/app/service.py`
- Create: `api/src/knowledge/app/__init__.py`

- [ ] **Step 1: Write the failing test**

Add to `api/tests/knowledge/test_service.py`:

```python
from src.knowledge.app.service import KnowledgeService


@pytest.mark.asyncio
async def test_service_ingest_delegates():
    store = AsyncMock()
    service = KnowledgeService(store)
    user_id = uuid4()

    await service.ingest(user_id, "some findings", {"source": "agent-a"})

    store.ingest.assert_awaited_once_with(
        user_id, "some findings", {"source": "agent-a"}
    )


@pytest.mark.asyncio
async def test_service_query_delegates():
    store = AsyncMock()
    store.query.return_value = "answer text"
    service = KnowledgeService(store)
    user_id = uuid4()

    result = await service.query(user_id, "what is X?", "hybrid")

    store.query.assert_awaited_once_with(user_id, "what is X?", "hybrid")
    assert result == "answer text"


@pytest.mark.asyncio
async def test_service_get_graph_delegates():
    store = AsyncMock()
    store.get_graph.return_value = {"nodes": [], "edges": []}
    service = KnowledgeService(store)
    user_id = uuid4()

    result = await service.get_graph(user_id)

    store.get_graph.assert_awaited_once_with(user_id)
    assert result == {"nodes": [], "edges": []}
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd api && pytest tests/knowledge/test_service.py::test_service_ingest_delegates -v
```

Expected: `ImportError` — `KnowledgeService` not found.

- [ ] **Step 3: Implement KnowledgeService**

`api/src/knowledge/app/service.py`:

```python
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
```

`api/src/knowledge/app/__init__.py`:

```python
from src.knowledge.app.service import KnowledgeService as KnowledgeApp

__all__ = ["KnowledgeApp"]
```

- [ ] **Step 4: Run tests**

```bash
cd api && pytest tests/knowledge/test_service.py -v
```

Expected: all 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add api/src/knowledge/app/
git commit -m "feat(knowledge): add KnowledgeService app layer"
```

---

## Task 6: Config — Knowledge Settings

**Files:**

- Modify: `api/src/shared/config.py`

- [ ] **Step 1: Write the failing test**

Add to `api/tests/knowledge/test_service.py`:

```python
from src.shared.config import Settings


def test_knowledge_settings_defaults():
    # Provide required fields, check knowledge fields default correctly
    s = Settings(
        database_url="postgresql://u:p@localhost/db",
        encryption_key="AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
    )
    assert s.knowledge_llm_model == "gpt-4o-mini"
    assert s.knowledge_embed_dim == 1536
    assert s.knowledge_embed_model == "text-embedding-3-small"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd api && pytest tests/knowledge/test_service.py::test_knowledge_settings_defaults -v
```

Expected: `ValidationError` or `AttributeError` — `knowledge_llm_model` field doesn't exist.

- [ ] **Step 3: Add knowledge fields to Settings**

In `api/src/shared/config.py`, add after `default_llm_model`:

```python
    # Knowledge graph (LightRAG) — LLM used for entity extraction at ingest time
    knowledge_llm_api_key: str = ""
    knowledge_llm_base_url: str = "https://api.openai.com/v1"
    knowledge_llm_model: str = "gpt-4o-mini"

    # Knowledge graph — embedding model for vector storage
    knowledge_embed_api_key: str = ""
    knowledge_embed_base_url: str = "https://api.openai.com/v1"
    knowledge_embed_model: str = "text-embedding-3-small"
    knowledge_embed_dim: int = 1536
```

- [ ] **Step 4: Run tests**

```bash
cd api && pytest tests/knowledge/test_service.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add api/src/shared/config.py
git commit -m "feat(knowledge): add knowledge LLM/embed settings to config"
```

---

## Task 7: REST Router

**Files:**

- Create: `api/src/knowledge/adapters/_in/router.py`

- [ ] **Step 1: Write the failing test**

Create `api/tests/knowledge/test_router.py`:

```python
import pytest
from unittest.mock import AsyncMock
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.knowledge.adapters._in.router import router
from src.knowledge.app import KnowledgeApp


@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(router, prefix="/knowledge")

    mock_knowledge = AsyncMock(spec=KnowledgeApp)
    mock_knowledge.query.return_value = "Paris"
    mock_knowledge.get_graph.return_value = {"nodes": [], "edges": []}

    app.state.knowledge = mock_knowledge
    app.state.pool = AsyncMock()  # needed by _require_user if present
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


def test_query_endpoint(client, app):
    user_id = str(uuid4())
    # Override get_knowledge_user_id dependency
    from src.knowledge.adapters._in.router import get_knowledge_user_id
    from uuid import UUID
    app.dependency_overrides[get_knowledge_user_id] = lambda: UUID(user_id)

    resp = client.post("/knowledge/query", json={"query": "capital of France?"})
    assert resp.status_code == 200
    assert resp.json()["answer"] == "Paris"


def test_graph_endpoint(client, app):
    user_id = str(uuid4())
    from src.knowledge.adapters._in.router import get_knowledge_user_id
    from uuid import UUID
    app.dependency_overrides[get_knowledge_user_id] = lambda: UUID(user_id)

    resp = client.get("/knowledge/graph")
    assert resp.status_code == 200
    assert "nodes" in resp.json()
    assert "edges" in resp.json()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd api && pytest tests/knowledge/test_router.py -v
```

Expected: `ImportError` — router not found.

- [ ] **Step 3: Implement router**

`api/src/knowledge/adapters/_in/router.py`:

```python
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, UploadFile, File

from src.knowledge.app import KnowledgeApp
from src.knowledge.core.schema import GraphData, IngestTextRequest, QueryRequest, QueryResponse

router = APIRouter()


def get_knowledge(request: Request) -> KnowledgeApp:
    return request.app.state.knowledge


async def get_knowledge_user_id(request: Request) -> UUID:
    """Extract user_id from session. Mirrors the auth pattern used elsewhere in the app."""
    from src.identity.app import IdentityApp
    identity: IdentityApp = request.app.state.identity
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        raise HTTPException(401, "Missing Authorization header")
    token = auth[7:]
    record = await identity.find_by_token(token)
    if not record:
        raise HTTPException(401, "Invalid token")
    return record["id"]


@router.post("/ingest/text", status_code=202)
async def ingest_text(
    body: IngestTextRequest,
    background_tasks: BackgroundTasks,
    knowledge: KnowledgeApp = Depends(get_knowledge),
    user_id: UUID = Depends(get_knowledge_user_id),
) -> dict:
    """Ingest raw text into the knowledge graph. Indexing runs in the background."""
    background_tasks.add_task(knowledge.ingest, user_id, body.text, body.metadata)
    return {"status": "queued"}


@router.post("/ingest/file", status_code=202)
async def ingest_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    knowledge: KnowledgeApp = Depends(get_knowledge),
    user_id: UUID = Depends(get_knowledge_user_id),
) -> dict:
    """Upload a file for background ingestion (txt, md, pdf)."""
    allowed = {"text/plain", "text/markdown", "application/pdf"}
    if file.content_type not in allowed:
        raise HTTPException(415, f"Unsupported file type: {file.content_type}")
    content = (await file.read()).decode("utf-8", errors="replace")
    background_tasks.add_task(knowledge.ingest, user_id, content, {"filename": file.filename})
    return {"status": "queued", "filename": file.filename}


@router.post("/query", response_model=QueryResponse)
async def query_knowledge(
    body: QueryRequest,
    knowledge: KnowledgeApp = Depends(get_knowledge),
    user_id: UUID = Depends(get_knowledge_user_id),
) -> QueryResponse:
    """Query the knowledge graph."""
    answer = await knowledge.query(user_id, body.query, body.mode)
    return QueryResponse(answer=answer)


@router.get("/graph", response_model=GraphData)
async def get_graph(
    knowledge: KnowledgeApp = Depends(get_knowledge),
    user_id: UUID = Depends(get_knowledge_user_id),
) -> GraphData:
    """Return graph nodes and edges for visualisation."""
    data = await knowledge.get_graph(user_id)
    return GraphData(
        nodes=data.get("nodes", []),
        edges=data.get("edges", []),
    )
```

- [ ] **Step 4: Run tests**

```bash
cd api && pytest tests/knowledge/ -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add api/src/knowledge/adapters/_in/router.py api/tests/knowledge/test_router.py
git commit -m "feat(knowledge): add REST router for ingest and query"
```

---

## Task 8: DI and main.py Integration

**Files:**

- Create: `api/src/knowledge/di.py`
- Modify: `api/src/entrypoint/main.py`

- [ ] **Step 1: Create di.py**

`api/src/knowledge/di.py`:

```python
from src.knowledge.adapters.out.lightrag_store import LightRAGStore
from src.knowledge.app import KnowledgeApp
from src.shared.config import Settings


def build(settings: Settings) -> KnowledgeApp:
    store = LightRAGStore(settings)
    return KnowledgeApp(store)
```

- [ ] **Step 2: Mount in main.py**

In `api/src/entrypoint/main.py`, add the import:

```python
import src.knowledge.di as knowledge_di
from src.knowledge.adapters._in.router import router as knowledge_router
```

In the `lifespan` function, after `identity = identity_di.build(...)`:

```python
    knowledge = knowledge_di.build(settings)
    app.state.knowledge = knowledge
```

Add the router in `create_app`:

```python
    app.include_router(knowledge_router, prefix="/knowledge", tags=["knowledge"])
```

The full updated `lifespan` block:

```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    pool = await asyncpg.create_pool(settings.database_url)

    integrations = integrations_di.build(pool)
    library = library_di.build(pool)
    fleet, watcher = fleet_di.build(pool, integrations, library)
    identity = identity_di.build(pool, fleet, integrations)
    knowledge = knowledge_di.build(settings)

    app.state.pool = pool
    app.state.fleet = fleet
    app.state.identity = identity
    app.state.library = library
    app.state.integrations = integrations
    app.state.knowledge = knowledge

    mcp_setup(
        pool=pool,
        fleet=fleet,
        identity=identity,
        library=library,
        integrations=integrations,
        knowledge=knowledge,
    )

    watcher.start()

    yield

    await watcher.stop()
    await pool.close()
```

- [ ] **Step 3: Verify app starts**

```bash
cd api && uvicorn src.entrypoint.main:app --reload --port 8000
```

Expected: server starts, no import errors. `GET http://localhost:8000/docs` shows `/knowledge/*` endpoints.

- [ ] **Step 4: Commit**

```bash
git add api/src/knowledge/di.py api/src/entrypoint/main.py
git commit -m "feat(knowledge): wire knowledge domain into app lifespan"
```

---

## Task 9: MCP Tools

**Files:**

- Modify: `api/src/entrypoint/mcp.py`

- [ ] **Step 1: Update setup() signature**

In `api/src/entrypoint/mcp.py`, add `_knowledge` global and update `setup()`:

```python
from src.knowledge.app import KnowledgeApp

_knowledge: KnowledgeApp | None = None


def setup(
    pool: asyncpg.Pool,
    fleet: FleetApp,
    identity: IdentityApp,
    library: LibraryApp,
    integrations: IntegrationsApp,
    knowledge: KnowledgeApp,
) -> None:
    global _pool, _fleet, _identity, _library, _integrations, _knowledge
    _pool = pool
    _fleet = fleet
    _identity = identity
    _library = library
    _integrations = integrations
    _knowledge = knowledge
```

- [ ] **Step 2: Add business logic functions**

After the existing `mcp_list_channels` function, add:

```python
async def mcp_ingest_knowledge(
    knowledge: KnowledgeApp, user_id: UUID, text: str, metadata: dict
) -> dict:
    await knowledge.ingest(user_id, text, metadata)
    return {"status": "queued"}


async def mcp_query_knowledge(
    knowledge: KnowledgeApp, user_id: UUID, query: str, mode: str
) -> dict:
    answer = await knowledge.query(user_id, query, mode)
    return {"answer": answer}
```

- [ ] **Step 3: Add MCP tool wrappers**

After the `list_channels` tool, add:

```python
@mcp.tool()
async def ingest_knowledge(
    context: Context,
    text: str,
    metadata_json: str = "{}",
) -> dict:
    """Ingest text into the shared knowledge graph.

    Use this when you have findings, research results, or facts worth preserving
    for the fleet. Indexing happens asynchronously — the tool returns immediately.

    metadata_json: optional JSON string with context e.g. {"source": "web", "topic": "AI"}.
    """
    import json
    user_id = await _require_user(context)
    _assert_ready()
    assert _knowledge is not None
    try:
        metadata = json.loads(metadata_json)
    except json.JSONDecodeError:
        metadata = {}
    return await mcp_ingest_knowledge(_knowledge, user_id, text, metadata)


@mcp.tool()
async def query_knowledge(
    context: Context,
    query: str,
    mode: str = "hybrid",
) -> dict:
    """Query the shared knowledge graph.

    Retrieves synthesised knowledge from all sources ingested by the fleet.

    mode options:
      "local"  — entity-focused retrieval (precise, narrow context)
      "global" — graph-wide traversal (broad, relationship-aware)
      "hybrid" — both combined (recommended default)
      "naive"  — vector similarity only (no graph reasoning)
    """
    user_id = await _require_user(context)
    _assert_ready()
    assert _knowledge is not None
    return await mcp_query_knowledge(_knowledge, user_id, query, mode)
```

- [ ] **Step 4: Run existing MCP tests**

```bash
cd api && pytest tests/ -v
```

Expected: all tests PASS. If there are MCP tests that test `setup()` signature, update them to pass a `knowledge=AsyncMock()` argument.

- [ ] **Step 5: Commit**

```bash
git add api/src/entrypoint/mcp.py
git commit -m "feat(knowledge): add ingest_knowledge and query_knowledge MCP tools"
```

---

## Task 10: Volume in compose.local.yml

**Files:**

- Modify: `compose.local.yml`

- [ ] **Step 1: Add kg_data volume**

Update `compose.local.yml`:

```yaml
services:
  registry:
    image: registry:2
    ports:
      - "5005:5000"
    restart: unless-stopped

  db:
    image: pgvector/pgvector:pg18
    ports:
      - "5434:5432"
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: postgres
    volumes:
      - ./postgres:/var/lib/postgresql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  api:
    build: ./api
    ports:
      - "8000:8000"
    env_file: api/.env
    environment:
      SANDBOX_RUNNER: docker
      SANDBOX_GATEWAY_HOST: host.docker.internal
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - /tmp/officeclaw:/tmp/officeclaw
      - ./api/uploads:/app/uploads
      - kg_data:/app/data/kg
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped

  web:
    build: ./web
    ports:
      - "3000:3000"
    env_file: web/.env
    depends_on:
      - api
    restart: unless-stopped

volumes:
  kg_data:
```

- [ ] **Step 2: Commit**

```bash
git add compose.local.yml
git commit -m "feat(knowledge): add kg_data volume for NetworkX graph persistence"
```

---

## Task 11: Env Variables

Add to `api/.env` (not committed — document in README or `.env.example`):

```bash
# Knowledge graph — LightRAG entity extraction LLM
KNOWLEDGE_LLM_API_KEY=sk-...
KNOWLEDGE_LLM_BASE_URL=https://api.openai.com/v1
KNOWLEDGE_LLM_MODEL=gpt-4o-mini

# Knowledge graph — embedding model
KNOWLEDGE_EMBED_API_KEY=sk-...
KNOWLEDGE_EMBED_BASE_URL=https://api.openai.com/v1
KNOWLEDGE_EMBED_MODEL=text-embedding-3-small
KNOWLEDGE_EMBED_DIM=1536
```

These can reuse the same key as `DEFAULT_LLM_API_KEY` if the provider supports both completions and embeddings.

- [ ] **Step 1: Add to api/.env.example if it exists, or document in CLAUDE.md note**

```bash
# Check if .env.example exists
ls api/.env.example 2>/dev/null || echo "no .env.example, add to CLAUDE.md env table"
```

- [ ] **Step 2: Verify full test suite**

```bash
cd api && pytest tests/ -v --tb=short
```

Expected: all tests PASS.

- [ ] **Step 3: Final commit**

```bash
git add .
git commit -m "feat(knowledge): complete LightRAG knowledge domain integration"
```

---

## Smoke Test (Manual)

After deploying:

```bash
# 1. Get your OFFICECLAW_TOKEN
TOKEN=your_token_here

# 2. Ingest some text
curl -X POST http://localhost:8000/knowledge/ingest/text \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text": "Paris is the capital of France. The Eiffel Tower was built in 1889."}'
# Expected: {"status": "queued"}

# 3. Wait ~10-30s for async entity extraction to complete

# 4. Query
curl -X POST http://localhost:8000/knowledge/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is notable about Paris?", "mode": "hybrid"}'
# Expected: {"answer": "Paris is the capital of France and home to the Eiffel Tower..."}

# 5. Check graph
curl http://localhost:8000/knowledge/graph \
  -H "Authorization: Bearer $TOKEN"
# Expected: {"nodes": [...Paris, Eiffel Tower...], "edges": [...]}
```

---

## Known Risks

| Risk                                                                                          | Mitigation                                                                                                                                                        |
| --------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `addon_params` is not the correct LightRAG API for PG connection config                       | Check LightRAG PGKVStorage source — may use `POSTGRES_*` env vars instead. Fallback: set env vars in `di.py` via `os.environ` before constructing `LightRAGStore` |
| `rag.chunk_entity_relation_graph._graph` is a private attribute                               | If it changes, inspect `rag.chunk_entity_relation_graph` for a public `export()` or `to_dict()` method                                                            |
| `openai_complete_if_cache` / `openai_embed` import path changes between lightrag-hku versions | Check `lightrag.llm` submodule after install. Alternative: use `openai.AsyncOpenAI` directly                                                                      |
| Ingest is slow (LLM calls per document)                                                       | Expected. Agents should be selective. Background task means no HTTP timeout risk                                                                                  |
