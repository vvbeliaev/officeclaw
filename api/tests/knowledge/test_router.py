import pytest
from unittest.mock import AsyncMock
from uuid import uuid4, UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.knowledge.adapters._in.router import router, get_knowledge_user_id
from src.knowledge.app import KnowledgeApp


@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(router, prefix="/knowledge")

    mock_knowledge = AsyncMock(spec=KnowledgeApp)
    mock_knowledge.query.return_value = "Paris"
    mock_knowledge.get_graph.return_value = {"nodes": [], "edges": []}

    app.state.knowledge = mock_knowledge
    return app


def test_query_endpoint(app):
    user_id = uuid4()
    app.dependency_overrides[get_knowledge_user_id] = lambda: user_id

    client = TestClient(app)
    resp = client.post("/knowledge/query", json={"query": "capital of France?"})
    assert resp.status_code == 200
    assert resp.json()["answer"] == "Paris"


def test_graph_endpoint(app):
    user_id = uuid4()
    app.dependency_overrides[get_knowledge_user_id] = lambda: user_id

    client = TestClient(app)
    resp = client.get("/knowledge/graph")
    assert resp.status_code == 200
    assert "nodes" in resp.json()
    assert "edges" in resp.json()


def test_ingest_text_endpoint(app):
    user_id = uuid4()
    app.dependency_overrides[get_knowledge_user_id] = lambda: user_id

    client = TestClient(app)
    resp = client.post(
        "/knowledge/ingest/text",
        json={"text": "Paris is the capital of France."},
    )
    assert resp.status_code == 202
    assert resp.json()["status"] == "queued"
