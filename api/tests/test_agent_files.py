# api/tests/test_agent_files.py
from uuid import UUID

import pytest


from tests.conftest import register_user


@pytest.fixture
async def agent_id(client, conn):
    body = await register_user(client, conn, "files-owner@example.com")
    agent = await client.post(
        "/agents", json={"workspace_id": body["workspace_id"], "name": "Agent"}
    )
    return agent.json()["id"]


async def test_upsert_and_get_file(client, agent_id, fleet_deps):
    resp = await client.put(
        f"/agents/{agent_id}/files",
        json={"path": "SOUL.md", "content": "You are a helpful agent."}
    )
    assert resp.status_code == 200
    assert resp.json()["path"] == "SOUL.md"
    record = await fleet_deps.find_file(UUID(agent_id), "SOUL.md")
    assert record["content"] == "You are a helpful agent."


async def test_list_files(client, agent_id, fleet_deps):
    await client.put(f"/agents/{agent_id}/files", json={"path": "SOUL.md", "content": "x"})
    await client.put(f"/agents/{agent_id}/files", json={"path": "AGENTS.md", "content": "y"})
    # agent fixture creates 3 seed files via bootstrap; filter to ours
    files = await fleet_deps.list_files(UUID(agent_id))
    paths = [f["path"] for f in files]
    assert "SOUL.md" in paths
    assert "AGENTS.md" in paths


async def test_upsert_overwrites(client, agent_id, fleet_deps):
    await client.put(f"/agents/{agent_id}/files", json={"path": "SOUL.md", "content": "v1"})
    await client.put(f"/agents/{agent_id}/files", json={"path": "SOUL.md", "content": "v2"})
    record = await fleet_deps.find_file(UUID(agent_id), "SOUL.md")
    assert record["content"] == "v2"
