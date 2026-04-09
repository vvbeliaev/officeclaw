# api/tests/test_admin.py
from uuid import UUID


async def test_create_user_returns_token(client):
    resp = await client.post("/users", json={"email": "admin-test@example.com"})
    assert resp.status_code == 201
    body = resp.json()
    assert "officeclaw_token" in body
    assert len(body["officeclaw_token"]) > 20


async def test_create_user_creates_admin_agent(client, fleet_deps):
    resp = await client.post("/users", json={"email": "admin-agent@example.com"})
    uid = UUID(resp.json()["id"])
    agents = await fleet_deps.list_agents(uid)
    admin_agents = [a for a in agents if a["is_admin"]]
    assert len(admin_agents) == 1
    assert admin_agents[0]["name"] == "Admin"


async def test_admin_agent_has_seed_files(client, fleet_deps):
    resp = await client.post("/users", json={"email": "admin-files@example.com"})
    uid = UUID(resp.json()["id"])
    agents = await fleet_deps.list_agents(uid)
    agent_id = next(a["id"] for a in agents if a["is_admin"])
    files = await fleet_deps.list_files(agent_id)
    paths = {f["path"] for f in files}
    assert "SOUL.md" in paths
    assert "AGENTS.md" in paths
    assert "TOOLS.md" in paths


async def test_admin_agent_has_mcp_config(client, fleet_deps, integrations_deps):
    resp = await client.post("/users", json={"email": "admin-mcp@example.com"})
    uid = UUID(resp.json()["id"])
    agents = await fleet_deps.list_agents(uid)
    agent_id = next(a["id"] for a in agents if a["is_admin"])
    mcp_list = await integrations_deps.list_agent_mcp(agent_id)
    names = [m["name"] for m in mcp_list]
    assert "officeclaw" in names


async def test_admin_agent_has_env_linked(client, fleet_deps, integrations_deps):
    resp = await client.post("/users", json={"email": "admin-env@example.com"})
    uid = UUID(resp.json()["id"])
    agents = await fleet_deps.list_agents(uid)
    agent_id = next(a["id"] for a in agents if a["is_admin"])
    envs = await integrations_deps.list_agent_envs(agent_id)
    assert len(envs) == 1
    assert envs[0]["name"] == "officeclaw"
