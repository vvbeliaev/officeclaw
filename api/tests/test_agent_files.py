# api/tests/test_agent_files.py
import pytest


@pytest.fixture
async def agent_id(client):
    user = await client.post("/users", json={"email": "files-owner@example.com"})
    uid = user.json()["id"]
    agent = await client.post("/agents", json={"user_id": uid, "name": "Agent"})
    return agent.json()["id"]


async def test_upsert_and_get_file(client, agent_id):
    resp = await client.put(
        f"/agents/{agent_id}/files",
        json={"path": "SOUL.md", "content": "You are a helpful agent."}
    )
    assert resp.status_code == 200
    assert resp.json()["path"] == "SOUL.md"
    resp2 = await client.get(f"/agents/{agent_id}/files/SOUL.md")
    assert resp2.status_code == 200
    assert resp2.json()["content"] == "You are a helpful agent."


async def test_list_files(client, agent_id):
    await client.put(f"/agents/{agent_id}/files", json={"path": "SOUL.md", "content": "x"})
    await client.put(f"/agents/{agent_id}/files", json={"path": "AGENTS.md", "content": "y"})
    resp = await client.get(f"/agents/{agent_id}/files")
    assert resp.status_code == 200
    paths = [f["path"] for f in resp.json()]
    assert "SOUL.md" in paths
    assert "AGENTS.md" in paths


async def test_upsert_overwrites(client, agent_id):
    await client.put(f"/agents/{agent_id}/files", json={"path": "SOUL.md", "content": "v1"})
    await client.put(f"/agents/{agent_id}/files", json={"path": "SOUL.md", "content": "v2"})
    resp = await client.get(f"/agents/{agent_id}/files/SOUL.md")
    assert resp.json()["content"] == "v2"
