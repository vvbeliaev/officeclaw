# api/tests/test_agents.py
from uuid import UUID

import pytest


@pytest.fixture
async def user_id(client):
    resp = await client.post("/users", json={"email": "agent-owner@example.com"})
    return resp.json()["id"]


async def test_create_agent(client, user_id):
    resp = await client.post("/agents", json={"user_id": user_id, "name": "My Agent"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "My Agent"
    assert body["status"] == "idle"
    assert body["is_admin"] is False


async def test_list_agents_for_user(client, user_id, fleet_deps):
    await client.post("/agents", json={"user_id": user_id, "name": "A1"})
    await client.post("/agents", json={"user_id": user_id, "name": "A2"})
    agents = await fleet_deps.list_agents(UUID(user_id))
    # user registration creates 1 Admin agent; 2 more added above = 3 total
    assert len(agents) == 3


async def test_update_agent_status(client, user_id):
    create = await client.post("/agents", json={"user_id": user_id, "name": "A"})
    agent_id = create.json()["id"]
    resp = await client.patch(f"/agents/{agent_id}", json={"status": "running", "sandbox_id": "sb-123"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "running"
    assert resp.json()["sandbox_id"] == "sb-123"


async def test_delete_agent(client, user_id, fleet_deps):
    create = await client.post("/agents", json={"user_id": user_id, "name": "A"})
    agent_id = create.json()["id"]
    assert (await client.delete(f"/agents/{agent_id}")).status_code == 204
    assert await fleet_deps.find_agent(UUID(agent_id)) is None
