import pytest
from uuid import UUID
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from src.knowledge.core.schema import IngestTextRequest, QueryRequest, QueryResponse, GraphData
from src.knowledge.adapters.out.lightrag_store import LightRAGStore


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
