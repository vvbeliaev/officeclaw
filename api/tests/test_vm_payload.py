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
    # Heartbeat defaults pulled from agent row (enabled=False, interval=1800).
    assert config["gateway"]["heartbeat"]["enabled"] is False
    assert config["gateway"]["heartbeat"]["intervalS"] == 1800
    # No crons attached → no jobs.json file.
    assert not any(f["path"] == "cron/jobs.json" for f in payload["files"])
    assert payload["env"]["OFFICECLAW_TOKEN"] == "tok-test"


async def test_vm_payload_renders_heartbeat_and_crons(client, conn):
    """When agent has heartbeat toggled on and crons attached, config.gateway
    reflects the column values and files contain cron/jobs.json."""
    from src.fleet.app.vm_payload import build_vm_payload
    import src.fleet.di as fleet_di
    import src.integrations.di as integrations_di
    import src.library.di as library_di

    body = await register_user(client, conn, "hb-cron@example.com")
    workspace_id = body["workspace_id"]

    agent = await client.post(
        "/agents", json={"workspace_id": workspace_id, "name": "PulseBot"}
    )
    agent_id = agent.json()["id"]

    await client.patch(
        f"/agents/{agent_id}",
        json={"heartbeat_enabled": True, "heartbeat_interval_s": 900},
    )

    cron = await client.post(
        "/crons",
        json={
            "workspace_id": workspace_id,
            "name": "hourly-digest",
            "schedule_kind": "every",
            "schedule_every_ms": 3_600_000,
            "message": "Summarise the hour.",
        },
    )
    cron_id = cron.json()["id"]
    await client.post(f"/agents/{agent_id}/crons/{cron_id}")

    integrations = integrations_di.build(conn)  # type: ignore[arg-type]
    library = library_di.build(conn)  # type: ignore[arg-type]
    fleet, _ = fleet_di.build(conn, integrations, library)  # type: ignore[arg-type]

    payload = await build_vm_payload(
        agent_id, fleet._agents, integrations, library, "tok-test", "UTC"  # type: ignore[arg-type]
    )
    config = json.loads(payload["config_json"])
    assert config["gateway"]["heartbeat"]["enabled"] is True
    assert config["gateway"]["heartbeat"]["intervalS"] == 900

    jobs_file = next(f for f in payload["files"] if f["path"] == "cron/jobs.json")
    jobs = json.loads(jobs_file["content"])
    assert jobs["version"] == 1
    assert len(jobs["jobs"]) == 1
    job = jobs["jobs"][0]
    assert job["name"] == "hourly-digest"
    assert job["schedule"]["kind"] == "every"
    assert job["schedule"]["everyMs"] == 3_600_000
    assert job["payload"]["message"] == "Summarise the hour."
    assert job["enabled"] is True


async def test_runtime_file_assembled_with_marker_when_template_attached(client, conn):
    """When a template + per-agent override both exist, the assembled body
    must contain the boundary marker — sandbox sync relies on it to strip the
    template before persisting the override back to agent_files.
    """
    from src.fleet.app.vm_payload import build_vm_payload
    from src.fleet.core.runtime_files import BOUNDARY_MARKER
    import src.fleet.di as fleet_di
    import src.integrations.di as integrations_di
    import src.library.di as library_di

    body = await register_user(client, conn, "marker-test@example.com")
    workspace_id = body["workspace_id"]

    agent = await client.post(
        "/agents", json={"workspace_id": workspace_id, "name": "MarkerAgent"}
    )
    agent_id = agent.json()["id"]

    await client.put(
        f"/agents/{agent_id}/files",
        json={"path": "SOUL.md", "content": "AGENT OVERRIDE"},
    )
    tpl = await client.post(
        "/templates",
        json={
            "workspace_id": workspace_id,
            "name": "shared-soul",
            "template_type": "soul",
            "content": "SHARED TEMPLATE",
        },
    )
    await client.post(f"/agents/{agent_id}/templates/{tpl.json()['id']}")

    integrations = integrations_di.build(conn)  # type: ignore[arg-type]
    library = library_di.build(conn)  # type: ignore[arg-type]
    fleet, _ = fleet_di.build(conn, integrations, library)  # type: ignore[arg-type]

    payload = await build_vm_payload(
        agent_id, fleet._agents, integrations, library, "tok-test", "UTC"  # type: ignore[arg-type]
    )
    soul = next(f for f in payload["files"] if f["path"] == "SOUL.md")
    assert soul["content"] == f"SHARED TEMPLATE\n{BOUNDARY_MARKER}\nAGENT OVERRIDE"
