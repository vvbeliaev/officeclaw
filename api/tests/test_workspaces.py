# api/tests/test_workspaces.py
from uuid import UUID

from tests.conftest import register_user


async def test_bootstrap_creates_workspace_with_token(client, conn):
    body = await register_user(client, conn, "ws-create@example.com")
    assert "workspace_id" in body
    assert "officeclaw_token" in body
    assert len(body["officeclaw_token"]) > 20


async def test_list_workspaces(client, conn):
    body = await register_user(client, conn, "ws-list@example.com")
    user_id = body["id"]
    resp = await client.get(f"/workspaces?user_id={user_id}")
    assert resp.status_code == 200
    workspaces = resp.json()
    assert len(workspaces) == 1
    assert workspaces[0]["name"] == "Personal"


async def test_create_second_workspace(client, conn):
    body = await register_user(client, conn, "ws-second@example.com")
    user_id = body["id"]
    resp = await client.post("/workspaces", json={"user_id": user_id, "name": "Work"})
    assert resp.status_code == 201
    ws = resp.json()
    assert ws["name"] == "Work"
    assert "officeclaw_token" in ws
    assert "id" in ws


async def test_second_workspace_has_admin_agent(client, conn, fleet_deps):
    body = await register_user(client, conn, "ws-admin@example.com")
    user_id = body["id"]
    ws_resp = await client.post("/workspaces", json={"user_id": user_id, "name": "Work"})
    workspace_id = UUID(ws_resp.json()["id"])
    agents = await fleet_deps.list_agents(workspace_id)
    admin = [a for a in agents if a["is_admin"]]
    assert len(admin) == 1
