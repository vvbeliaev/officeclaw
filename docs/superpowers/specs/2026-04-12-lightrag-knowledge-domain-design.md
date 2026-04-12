# LightRAG Knowledge Domain — Design

**Date:** 2026-04-12
**Status:** Approved

---

## Overview

Add a shared knowledge graph layer to OfficeClaw using LightRAG. Every user's agent fleet shares one knowledge graph — agents write research findings, all agents can query. The graph is the "knowledge bus" of the fleet: agent A indexes a discovery, agent B retrieves it without duplication of effort.

LightRAG provides graph-based RAG combining entity extraction, relationship mapping, and hybrid retrieval (local/global). On ingest it calls an LLM to extract entities and relationships; on query it traverses the graph to return contextually rich answers.

---

## Goals

- Agents can ingest text/findings into a shared per-user knowledge graph via MCP tool
- Agents can query the graph via MCP tool
- Users can upload documents (files) from the web UI
- Graph persists across agent VM restarts
- Per-user isolation: one graph per user, no cross-user leakage
- MVP: test whether the shared knowledge bus is actually useful before investing in heavy infrastructure

---

## Architecture

### New Domain: `api/src/knowledge/`

Follows the same hexagonal layout as `fleet`, `library`, `integrations`:

```
api/src/knowledge/
  core/
    schema.py          # IngestRequest, QueryRequest, QueryResponse, GraphData
    ports/
      _in.py           # IKnowledgeApp — inbound protocol
      out.py           # IKnowledgeStore — outbound protocol
  app/
    __init__.py        # KnowledgeApp facade — single entry point
    service.py         # KnowledgeService — ingest, query, get_graph use cases
  adapters/
    _in/
      router.py        # FastAPI router
    out/
      lightrag.py      # LightRAGStore — implements IKnowledgeStore
  di.py                # Wires LightRAGStore into KnowledgeService, returns KnowledgeApp
```

### Outbound Port

`IKnowledgeStore` is not a thin DB adapter — LightRAG owns both storage and LLM-based processing. The port reflects this:

```python
class IKnowledgeStore(Protocol):
    async def ingest(self, user_id: UUID, text: str, metadata: dict) -> None: ...
    async def query(self, user_id: UUID, query: str, mode: str) -> str: ...
    async def get_graph(self, user_id: UUID) -> dict: ...  # nodes + edges for UI
```

### LightRAGStore — Instance Cache

One LightRAG instance per user, lazily created and cached for the lifetime of the process:

```python
class LightRAGStore:
    def __init__(self, llm_func, embed_func, pg_config: dict) -> None:
        self._instances: dict[UUID, LightRAG] = {}
        self._llm_func = llm_func
        self._embed_func = embed_func
        self._pg_config = pg_config

    async def _get_or_create(self, user_id: UUID) -> LightRAG:
        if user_id not in self._instances:
            rag = LightRAG(
                working_dir="data/kg",
                workspace=str(user_id),         # per-user isolation
                llm_model_func=self._llm_func,
                embedding_func=self._embed_func,
                kv_storage="PGKVStorage",
                vector_storage="PGVectorStorage",
                graph_storage="NetworkXStorage", # data/kg/{user_id}/*.graphml
                doc_status_storage="PGDocStatusStorage",
                # pg connection string injected via env
            )
            await rag.initialize()              # required: sets up storage connections
            self._instances[user_id] = rag
        return self._instances[user_id]
```

---

## Storage

### Mixed Backend

| Layer                          | Backend              | Location                                                       |
| ------------------------------ | -------------------- | -------------------------------------------------------------- |
| KV (text chunks, entity cache) | `PGKVStorage`        | Postgres — `lightrag_kv_store`                                 |
| Vector (embeddings)            | `PGVectorStorage`    | Postgres — `lightrag_vector_store` (pgvector)                  |
| Graph (entities + relations)   | `NetworkXStorage`    | File — `data/kg/{user_id}/graph_chunk_entity_relation.graphml` |
| Doc status                     | `PGDocStatusStorage` | Postgres — `lightrag_doc_status`                               |

### Why This Combination

- `pgvector/pgvector:pg18` already in `compose.local.yml` — PGVectorStorage works without changes
- `PGGraphStorage` requires Apache AGE extension — not in current image, adds infrastructure complexity
- NetworkX graph is soft state: reloads from disk on restart, no data loss
- Pragmatic MVP tradeoff: validate the hypothesis before adding AGE

### Postgres Tables

LightRAG auto-creates its tables on first `initialize()` call. Tables are prefixed `lightrag_*` to avoid collision with OfficeClaw app tables. The `workspace` column provides per-user isolation.

Add to `001_initial_schema.sql` (already have pgvector image, just needs the extension):

```sql
CREATE EXTENSION IF NOT EXISTS vector;
-- lightrag_* tables are created by LightRAG on first use
```

### Volume

`data/kg/` must be a mounted volume so NetworkX `.graphml` files persist across container restarts. Add to `compose.local.yml`:

```yaml
services:
  api:
    volumes:
      - kg_data:/app/data/kg
volumes:
  kg_data:
```

---

## Statefulness

`KnowledgeApp` in `app.state.knowledge` holds `LightRAGStore` which caches `dict[UUID, LightRAG]`. This is **soft state**:

- On restart: LightRAG instances are recreated lazily; graphs reload from `data/kg/{user_id}/`. No data loss.
- On scale-out (multiple api replicas): NetworkX graphs diverge in memory → writes from different replicas do not sync. **Not safe for multi-replica deployments.**

Acceptable for MVP (single replica). Migration path: swap `NetworkXStorage` → `PGGraphStorage` (requires AGE) or `Neo4JStorage` in `di.py` when scale-out becomes necessary. The port interface does not change.

---

## API Surface

### REST Endpoints — `adapters/_in/router.py`

Mounted at `/knowledge` in `main.py`:

```
POST /knowledge/ingest/text    — ingest raw text (body: {text, metadata?})
POST /knowledge/ingest/file    — upload file (PDF, txt, md) → background ingest
POST /knowledge/query          — query graph (body: {query, mode?})
GET  /knowledge/graph          — return graph nodes+edges for web/ visualization
```

Authentication: all endpoints require the user to be identified. Pattern follows existing routes — user_id derived from session/token.

File ingest runs as `BackgroundTask` (FastAPI): HTTP returns 202 immediately, indexing happens async. LightRAG ingest involves LLM calls (entity extraction) — can take seconds to minutes depending on document size.

### MCP Tools — `entrypoint/mcp.py`

Two new tools added to the existing OfficeClaw MCP server:

```python
@mcp.tool()
async def ingest_knowledge(context: Context, text: str, metadata: str = "{}") -> dict:
    """Ingest text into the shared knowledge graph.
    Use this when you have findings, research results, or facts worth preserving.
    metadata: optional JSON string with source, topic, agent_id, etc.
    Returns: {status: "queued", doc_id: "..."}
    """

@mcp.tool()
async def query_knowledge(context: Context, query: str, mode: str = "hybrid") -> dict:
    """Query the shared knowledge graph.
    mode: "local" (entity-focused), "global" (graph-wide), "hybrid" (both), "naive" (vector-only)
    Returns: {answer: "...", sources: [...]}
    """
```

Both tools extract `user_id` via existing `_require_user()` helper.

---

## Initialization Order

In `main.py` lifespan, `knowledge` builds last — it has no dependencies on other OfficeClaw domains:

```python
integrations = integrations_di.build(pool)
library = library_di.build(pool)
fleet = fleet_di.build(pool, integrations, library)
identity = identity_di.build(pool, fleet, integrations)
knowledge = knowledge_di.build()          # no pool dependency — uses own PG connection
app.state.knowledge = knowledge
```

LightRAG manages its own Postgres connections (separate from the asyncpg pool). Same `DATABASE_URL` env var, different connection pool. Two pools to the same database is standard practice.

---

## LLM Configuration

LightRAG requires two functions at construction time:

- `llm_model_func` — for entity extraction at ingest time
- `embedding_func` — for vector embeddings

These are configured globally in `di.py`, not per-user. For MVP: use the same LLM provider as the rest of the system (configured via `LLM_API_KEY`, `LLM_BASE_URL` env vars). LightRAG supports OpenAI-compatible APIs.

This means ingest calls cost LLM tokens. Each document ingest = entity extraction pass over the text. This is a known cost center — agents should be selective about what they ingest.

---

## Env Variables

| Service | Key                       | Purpose                                   |
| ------- | ------------------------- | ----------------------------------------- |
| api     | `KNOWLEDGE_LLM_API_KEY`   | LLM API key for entity extraction         |
| api     | `KNOWLEDGE_LLM_MODEL`     | Model name (e.g. `google/gemma-4-31b-it`) |
| api     | `KNOWLEDGE_EMBED_MODEL`   | Embedding model name                      |
| api     | `KNOWLEDGE_EMBED_API_KEY` | Embedding API key (may differ from LLM)   |

Uses existing `DATABASE_URL` for Postgres KV/vector/doc-status storage.

---

## Visualization

`GET /knowledge/graph` returns:

```json
{
  "nodes": [
    { "id": "Entity Name", "type": "PERSON|ORG|...", "description": "..." }
  ],
  "edges": [
    { "source": "A", "target": "B", "label": "WORKS_FOR", "weight": 1.0 }
  ]
}
```

Web UI (`web/`) adds a graph visualization page using this endpoint. Library choice (Sigma.js, D3, Cytoscape) is a frontend decision — not part of this spec.

---

## Implementation Notes

### LightRAG Library vs lightrag-server

This design uses **LightRAG as a Python library**, not `lightrag-server`. The distinction matters:

- `lightrag-server` has a `LIGHTRAG-WORKSPACE` HTTP header — this is scaffolding for a future per-request workspace feature, currently only wired to `/health`. It does **not** enable multi-tenant operation in a single server process.
- The **LightRAG library** `workspace` parameter works correctly at construction time: it controls the subdirectory prefix for file backends and the `workspace` column for Postgres backends. This is what we use.

Per-user isolation is achieved by instantiating one `LightRAG(workspace=str(user_id))` per user. `lightrag-server` is never run — the library is embedded directly in `api/`.

### Async Initialization

Every `LightRAG` instance must have `await rag.initialize()` called before first use. The `LightRAGStore._get_or_create()` method handles this lazily on first access per user.

---

## What This Does NOT Cover

- Cross-user knowledge sharing (explicitly out of scope — workspace = user_id)
- Automatic ingest from agent conversations (agents call `ingest_knowledge` explicitly)
- Knowledge graph versioning or rollback
- Scaling beyond single replica (requires backend swap, not redesign)
- Visualization implementation in web/ (separate frontend task)
