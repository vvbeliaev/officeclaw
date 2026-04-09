import pytest


@pytest.fixture
async def setup(client):
    user = await client.post("/users", json={"email": "links@example.com"})
    uid = user.json()["id"]
    agent = await client.post("/agents", json={"user_id": uid, "name": "Agent"})
    skill = await client.post("/skills", json={"user_id": uid, "name": "research"})
    env = await client.post("/envs", json={"user_id": uid, "name": "anthropic", "values": {"K": "V"}})
    channel = await client.post("/channels", json={"user_id": uid, "type": "telegram", "config": {}})
    return {
        "agent_id": agent.json()["id"],
        "skill_id": skill.json()["id"],
        "env_id": env.json()["id"],
        "channel_id": channel.json()["id"],
    }


async def test_attach_detach_skill(client, setup):
    agent_id, skill_id = setup["agent_id"], setup["skill_id"]
    assert (await client.post(f"/agents/{agent_id}/skills/{skill_id}")).status_code == 204
    links = await client.get(f"/agents/{agent_id}/skills")
    assert any(s["id"] == skill_id for s in links.json())
    assert (await client.delete(f"/agents/{agent_id}/skills/{skill_id}")).status_code == 204


async def test_attach_detach_env(client, setup):
    agent_id, env_id = setup["agent_id"], setup["env_id"]
    await client.post(f"/agents/{agent_id}/envs/{env_id}")
    envs = await client.get(f"/agents/{agent_id}/envs")
    assert any(e["id"] == env_id for e in envs.json())
    resp2 = await client.delete(f"/agents/{agent_id}/envs/{env_id}")
    assert resp2.status_code == 204


async def test_attach_detach_channel(client, setup):
    agent_id, channel_id = setup["agent_id"], setup["channel_id"]
    resp = await client.post(f"/agents/{agent_id}/channels/{channel_id}")
    assert resp.status_code == 204
    channels = await client.get(f"/agents/{agent_id}/channels")
    assert any(c["id"] == channel_id for c in channels.json())
    resp2 = await client.delete(f"/agents/{agent_id}/channels/{channel_id}")
    assert resp2.status_code == 204


async def test_add_mcp(client, setup):
    agent_id = setup["agent_id"]
    resp = await client.post(f"/agents/{agent_id}/mcp", json={
        "name": "officeclaw",
        "config": {"url": "http://mcp:8700/mcp", "headers": {"Authorization": "Bearer tok"}}
    })
    assert resp.status_code == 201
    assert resp.json()["name"] == "officeclaw"
    assert "config" not in resp.json()
