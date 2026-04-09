# api/tests/test_admin.py


async def test_create_user_returns_token(client):
    resp = await client.post("/users", json={"email": "admin-test@example.com"})
    assert resp.status_code == 201
    body = resp.json()
    assert "officeclaw_token" in body
    assert len(body["officeclaw_token"]) > 20


async def test_create_user_creates_admin_agent(client):
    resp = await client.post("/users", json={"email": "admin-agent@example.com"})
    uid = resp.json()["id"]
    agents = await client.get(f"/agents?user_id={uid}")
    assert agents.status_code == 200
    admin_agents = [a for a in agents.json() if a["is_admin"]]
    assert len(admin_agents) == 1
    assert admin_agents[0]["name"] == "Admin"


async def test_admin_agent_has_seed_files(client):
    resp = await client.post("/users", json={"email": "admin-files@example.com"})
    uid = resp.json()["id"]
    agents = await client.get(f"/agents?user_id={uid}")
    agent_id = next(a["id"] for a in agents.json() if a["is_admin"])

    files = await client.get(f"/agents/{agent_id}/files")
    paths = {f["path"] for f in files.json()}
    assert "SOUL.md" in paths
    assert "AGENTS.md" in paths
    assert "TOOLS.md" in paths


async def test_admin_agent_has_mcp_config(client):
    resp = await client.post("/users", json={"email": "admin-mcp@example.com"})
    uid = resp.json()["id"]
    agents = await client.get(f"/agents?user_id={uid}")
    agent_id = next(a["id"] for a in agents.json() if a["is_admin"])

    mcp_list = await client.get(f"/agents/{agent_id}/mcp")
    names = [m["name"] for m in mcp_list.json()]
    assert "officeclaw" in names


async def test_admin_agent_has_env_linked(client):
    resp = await client.post("/users", json={"email": "admin-env@example.com"})
    uid = resp.json()["id"]
    agents = await client.get(f"/agents?user_id={uid}")
    agent_id = next(a["id"] for a in agents.json() if a["is_admin"])

    envs = await client.get(f"/agents/{agent_id}/envs")
    assert len(envs.json()) == 1
    assert envs.json()[0]["name"] == "officeclaw"
