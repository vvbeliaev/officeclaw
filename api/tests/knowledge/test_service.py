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
