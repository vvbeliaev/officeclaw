# api/tests/test_workspaces.py
from uuid import UUID
import pytest


async def test_create_workspace_returns_record(client):
    user_resp = await client.post("/users", json={"email": "ws-create@example.com"})
    assert user_resp.status_code == 201
    body = user_resp.json()
    assert "workspace_id" in body
    assert "officeclaw_token" in body
    assert len(body["officeclaw_token"]) > 20


async def test_list_workspaces(client):
    user_resp = await client.post("/users", json={"email": "ws-list@example.com"})
    user_id = user_resp.json()["id"]
    resp = await client.get(f"/workspaces?user_id={user_id}")
    assert resp.status_code == 200
    workspaces = resp.json()
    assert len(workspaces) == 1
    assert workspaces[0]["name"] == "Personal"


async def test_create_second_workspace(client):
    user_resp = await client.post("/users", json={"email": "ws-second@example.com"})
    user_id = user_resp.json()["id"]
    resp = await client.post("/workspaces", json={"user_id": user_id, "name": "Work"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Work"
    assert "officeclaw_token" in body
    assert "id" in body


async def test_second_workspace_has_admin_agent(client, fleet_deps):
    user_resp = await client.post("/users", json={"email": "ws-admin@example.com"})
    user_id = user_resp.json()["id"]
    ws_resp = await client.post("/workspaces", json={"user_id": user_id, "name": "Work"})
    workspace_id = UUID(ws_resp.json()["id"])
    agents = await fleet_deps.list_agents(workspace_id)
    admin = [a for a in agents if a["is_admin"]]
    assert len(admin) == 1
