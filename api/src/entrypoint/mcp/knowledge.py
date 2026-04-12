"""Knowledge graph tools — ingest text and query the shared knowledge graph."""

import json
from uuid import UUID

import src.entrypoint.mcp as _pkg
from fastmcp.server.context import Context
from src.knowledge.app import KnowledgeApp


async def mcp_ingest_knowledge(
    knowledge: KnowledgeApp, user_id: UUID, text: str, metadata: dict
) -> dict:
    await knowledge.ingest(user_id, text, metadata)
    return {"status": "ingested"}


async def mcp_query_knowledge(
    knowledge: KnowledgeApp, user_id: UUID, query: str, mode: str
) -> dict:
    answer = await knowledge.query(user_id, query, mode)
    return {"answer": answer}


@_pkg.mcp.tool()
async def ingest_knowledge(
    context: Context,
    text: str,
    metadata_json: str = "{}",
) -> dict:
    """Ingest text into the shared knowledge graph.

    Use this when you have findings, research results, or facts worth preserving
    for the fleet. Indexing may take several seconds depending on document size — the tool blocks until complete.

    metadata_json: optional JSON string e.g. {"source": "web", "topic": "AI"}.
    """
    user_id = await _pkg._require_user(context)
    _pkg._assert_ready()
    assert _pkg._knowledge is not None
    try:
        metadata = json.loads(metadata_json)
    except json.JSONDecodeError:
        metadata = {}
    return await mcp_ingest_knowledge(_pkg._knowledge, user_id, text, metadata)


@_pkg.mcp.tool()
async def query_knowledge(
    context: Context,
    query: str,
    mode: str = "hybrid",
) -> dict:
    """Query the shared knowledge graph.

    Retrieves synthesised knowledge from all sources ingested by the fleet.

    mode options:
      "local"  — entity-focused retrieval
      "global" — graph-wide traversal
      "hybrid" — both combined (recommended)
      "naive"  — vector similarity only
    """
    user_id = await _pkg._require_user(context)
    _pkg._assert_ready()
    assert _pkg._knowledge is not None
    return await mcp_query_knowledge(_pkg._knowledge, user_id, query, mode)
