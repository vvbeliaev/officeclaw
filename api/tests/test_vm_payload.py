# api/tests/test_vm_payload.py
import pytest
import json

from tests.conftest import register_user


@pytest.fixture
async def full_agent(client, conn):
    """Create user -> agent -> files -> skill -> env -> channel -> mcp."""
    body = await register_user(client, conn, "payload@example.com")
    workspace_id = body["workspace_id"]

    agent = await client.post("/agents", json={"workspace_id": workspace_id, "name": "Agent"})
    agent_id = agent.json()["id"]

    await client.put(
        f"/agents/{agent_id}/files",
        json={"path": "SOUL.md", "content": "You are helpful."},
    )
    await client.put(
        f"/agents/{agent_id}/files", json={"path": "AGENTS.md", "content": "# Agents"}
    )

    skill = await client.post("/skills", json={"workspace_id": workspace_id, "name": "research"})
    skill_id = skill.json()["id"]
    await client.put(
        f"/skills/{skill_id}/files", json={"path": "SKILL.md", "content": "# Research"}
    )
    await client.post(f"/agents/{agent_id}/skills/{skill_id}")

    env = await client.post(
        "/envs",
        json={
            "workspace_id": workspace_id,
            "name": "anthropic",
            "values": {"ANTHROPIC_API_KEY": "sk-test"},
        },
    )
    await client.post(f"/agents/{agent_id}/envs/{env.json()['id']}")

    channel = await client.post(
        "/channels",
        json={
            "workspace_id": workspace_id,
            "name": "telegram",
            "type": "telegram",
            "config": {"token": "bot:999", "allow_from": ["12345"]},
        },
    )
    await client.post(f"/agents/{agent_id}/channels/{channel.json()['id']}")

    mcp = await client.post(
        "/user-mcp",
        json={
            "workspace_id": workspace_id,
            "name": "officeclaw",
            "type": "http",
            "config": {
                "url": "http://mcp:8700/mcp",
                "headers": {"Authorization": "Bearer tok"},
            },
        },
    )
    await client.post(f"/agents/{agent_id}/mcp/{mcp.json()['id']}")

    return agent_id


async def test_vm_payload_structure(client, full_agent, conn):
    from src.fleet.app.vm_payload import build_vm_payload
    import src.fleet.di as fleet_di
    import src.integrations.di as integrations_di
    import src.library.di as library_di

    integrations = integrations_di.build(conn)  # type: ignore[arg-type]
    library = library_di.build(conn)  # type: ignore[arg-type]
    fleet, _ = fleet_di.build(conn, integrations, library)  # type: ignore[arg-type]

    payload = await build_vm_payload(
        full_agent, fleet._agents, integrations, library, "tok-test", "Europe/Berlin"  # type: ignore[arg-type]
    )

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
    # All agents use the single openai-compat "custom" provider slot,
    # forced via agents.defaults.provider so nanobot bypasses keyword-
    # based matching entirely. Secrets stay in env vars.
    assert config["agents"]["defaults"]["provider"] == "custom"
    assert config["agents"]["defaults"]["model"] == "${OFFICECLAW_LLM_MODEL}"
    assert config["providers"]["custom"]["api_key"] == "${OFFICECLAW_LLM_API_KEY}"
    assert config["providers"]["custom"]["api_base"] == "${OFFICECLAW_LLM_BASE_URL}"
    assert config["channels"]["telegram"]["token"] == "${TELEGRAM_TOKEN}"
    assert config["tools"]["mcpServers"]["officeclaw"]["url"] == "http://mcp:8700/mcp"
    assert config["agents"]["defaults"]["timezone"] == "Europe/Berlin"
    assert config["agents"]["defaults"]["skill_evolution"] is False
    assert config["tools"]["web"]["search"]["provider"] == "${OFFICECLAW_WEB_SEARCH_PROVIDER}"
    assert config["tools"]["web"]["search"]["api_key"] == "${OFFICECLAW_WEB_SEARCH_API_KEY}"
    assert payload["env"]["OFFICECLAW_TOKEN"] == "tok-test"
