# api/tests/test_links.py
from uuid import UUID

import pytest

from tests.conftest import register_user


@pytest.fixture
async def setup(client, conn):
    body = await register_user(client, conn, "links@example.com")
    workspace_id = body["workspace_id"]
    agent = await client.post("/agents", json={"workspace_id": workspace_id, "name": "Agent"})
    skill = await client.post("/skills", json={"workspace_id": workspace_id, "name": "research"})
    env = await client.post("/envs", json={"workspace_id": workspace_id, "name": "anthropic", "values": {"K": "V"}})
    channel = await client.post("/channels", json={"workspace_id": workspace_id, "name": "telegram", "type": "telegram", "config": {}})
    mcp = await client.post("/user-mcp", json={"workspace_id": workspace_id, "name": "officeclaw", "type": "http", "config": {"url": "http://mcp:8700/mcp", "headers": {"Authorization": "Bearer tok"}}})
    return {
        "workspace_id": workspace_id,
        "agent_id": agent.json()["id"],
        "skill_id": skill.json()["id"],
        "env_id": env.json()["id"],
        "channel_id": channel.json()["id"],
        "mcp_id": mcp.json()["id"],
    }


async def test_attach_detach_skill(client, setup, integrations_deps):
    agent_id, skill_id = UUID(setup["agent_id"]), UUID(setup["skill_id"])
    assert (await client.post(f"/agents/{agent_id}/skills/{skill_id}")).status_code == 204
    links = await integrations_deps.list_agent_skills(agent_id)
    assert any(str(s["id"]) == str(skill_id) for s in links)
    assert (await client.delete(f"/agents/{agent_id}/skills/{skill_id}")).status_code == 204


async def test_attach_detach_env(client, setup, integrations_deps):
    agent_id, env_id = UUID(setup["agent_id"]), UUID(setup["env_id"])
    await client.post(f"/agents/{agent_id}/envs/{env_id}")
    envs = await integrations_deps.list_agent_envs(agent_id)
    assert any(str(e["id"]) == str(env_id) for e in envs)
    assert (await client.delete(f"/agents/{agent_id}/envs/{env_id}")).status_code == 204


async def test_attach_detach_channel(client, setup, integrations_deps):
    agent_id, channel_id = UUID(setup["agent_id"]), UUID(setup["channel_id"])
    assert (await client.post(f"/agents/{agent_id}/channels/{channel_id}")).status_code == 204
    channels = await integrations_deps.list_agent_channels(agent_id)
    assert any(str(c["id"]) == str(channel_id) for c in channels)
    assert (await client.delete(f"/agents/{agent_id}/channels/{channel_id}")).status_code == 204


async def test_add_mcp(client, setup, integrations_deps):
    agent_id, mcp_id = UUID(setup["agent_id"]), UUID(setup["mcp_id"])
    resp = await client.post(f"/agents/{agent_id}/mcp/{mcp_id}")
    assert resp.status_code == 204
    mcps = await integrations_deps.list_agent_mcps(agent_id)
    assert any(str(m["id"]) == str(mcp_id) for m in mcps)


async def test_attach_detach_cron(client, setup, integrations_deps):
    agent_id = UUID(setup["agent_id"])
    cron = await client.post(
        "/crons",
        json={
            "workspace_id": setup["workspace_id"],
            "name": "daily-digest",
            "schedule_kind": "cron",
            "schedule_expr": "0 9 * * *",
            "schedule_tz": "UTC",
            "message": "Summarise yesterday.",
        },
    )
    assert cron.status_code == 201, cron.text
    cron_id = UUID(cron.json()["id"])

    assert (await client.post(f"/agents/{agent_id}/crons/{cron_id}")).status_code == 204
    links = await integrations_deps.list_agent_crons(agent_id)
    assert any(r["id"] == cron_id for r in links)
    assert all(r["enabled"] for r in links if r["id"] == cron_id)

    # Pause the attachment.
    patch_resp = await client.patch(
        f"/agents/{agent_id}/crons/{cron_id}", json={"enabled": False}
    )
    assert patch_resp.status_code == 200, patch_resp.text
    assert patch_resp.json()["enabled"] is False

    assert (await client.delete(f"/agents/{agent_id}/crons/{cron_id}")).status_code == 204
    links = await integrations_deps.list_agent_crons(agent_id)
    assert not any(r["id"] == cron_id for r in links)


async def test_cron_schedule_validation(client, setup):
    # 'every' without every_ms → 422
    bad = await client.post(
        "/crons",
        json={
            "workspace_id": setup["workspace_id"],
            "name": "bad-1",
            "schedule_kind": "every",
        },
    )
    assert bad.status_code == 422

    # tz on non-cron schedule → 422
    bad_tz = await client.post(
        "/crons",
        json={
            "workspace_id": setup["workspace_id"],
            "name": "bad-2",
            "schedule_kind": "every",
            "schedule_every_ms": 60_000,
            "schedule_tz": "UTC",
        },
    )
    assert bad_tz.status_code == 422
