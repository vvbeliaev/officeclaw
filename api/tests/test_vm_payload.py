# api/tests/test_vm_payload.py
import pytest
import json


@pytest.fixture
async def full_agent(client):
    """Create user -> agent -> files -> skill -> env -> channel -> mcp."""
    user = await client.post("/users", json={"email": "payload@example.com"})
    uid = user.json()["id"]

    agent = await client.post("/agents", json={"user_id": uid, "name": "Agent"})
    agent_id = agent.json()["id"]

    await client.put(f"/agents/{agent_id}/files", json={"path": "SOUL.md", "content": "You are helpful."})
    await client.put(f"/agents/{agent_id}/files", json={"path": "AGENTS.md", "content": "# Agents"})

    skill = await client.post("/skills", json={"user_id": uid, "name": "research"})
    skill_id = skill.json()["id"]
    await client.put(f"/skills/{skill_id}/files", json={"path": "SKILL.md", "content": "# Research"})
    await client.post(f"/agents/{agent_id}/skills/{skill_id}")

    env = await client.post("/envs", json={"user_id": uid, "name": "anthropic", "values": {"ANTHROPIC_API_KEY": "sk-test"}})
    await client.post(f"/agents/{agent_id}/envs/{env.json()['id']}")

    channel = await client.post("/channels", json={
        "user_id": uid, "type": "telegram",
        "config": {"token": "bot:999", "allow_from": ["12345"]}
    })
    await client.post(f"/agents/{agent_id}/channels/{channel.json()['id']}")

    await client.post(f"/agents/{agent_id}/mcp", json={
        "name": "officeclaw",
        "config": {"url": "http://mcp:8700/mcp", "headers": {"Authorization": "Bearer tok"}}
    })

    return agent_id


async def test_vm_payload_structure(client, full_agent, conn):
    from src.fleet.adapters.outbound.vm_payload import build_vm_payload
    payload = await build_vm_payload(conn, full_agent)

    # Files
    paths = {f["path"] for f in payload["files"]}
    assert "SOUL.md" in paths
    assert "AGENTS.md" in paths
    assert "skills/research/SKILL.md" in paths

    # Env vars
    assert payload["env"]["ANTHROPIC_API_KEY"] == "sk-test"

    # config.json
    config = json.loads(payload["config_json"])
    assert config["agents"]["defaults"]["workspace"] == "/workspace"
    assert config["providers"]["anthropic"]["apiKey"] == "${ANTHROPIC_API_KEY}"
    assert config["channels"]["telegram"]["token"] == "${TELEGRAM_TOKEN}"
    assert config["tools"]["mcpServers"]["officeclaw"]["url"] == "http://mcp:8700/mcp"
