# api/tests/test_mcp_tools.py
import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from src.entrypoint.mcp import (
    mcp_attach_skill,
    mcp_create_agent,
    mcp_create_env,
    mcp_create_skill,
    mcp_delete_agent,
    mcp_get_fleet_status,
    mcp_list_agents,
    mcp_list_channels,
    mcp_list_envs,
    mcp_list_skills,
    mcp_start_agent,
    mcp_stop_agent,
    mcp_update_agent_file,
)


async def test_mcp_list_agents(mcp_conn_user, fleet_deps):
    conn, user_id = mcp_conn_user
    agents = await mcp_list_agents(fleet_deps, user_id)
    assert any(a["name"] == "Admin" for a in agents)


async def test_mcp_get_fleet_status(mcp_conn_user, fleet_deps):
    conn, user_id = mcp_conn_user
    status = await mcp_get_fleet_status(fleet_deps, user_id)
    assert "agents" in status
    assert "summary" in status
    assert set(status["summary"].keys()) == {"idle", "running", "error"}


async def test_mcp_create_agent(mcp_conn_user, fleet_deps):
    conn, user_id = mcp_conn_user
    result = await mcp_create_agent(fleet_deps, user_id, "MyBot", "ghcr.io/hkuds/nanobot:latest")
    assert result["name"] == "MyBot"
    assert result["status"] == "idle"
    assert "id" in result


async def test_mcp_update_agent_file(mcp_conn_user, fleet_deps):
    conn, user_id = mcp_conn_user
    agent = await mcp_create_agent(fleet_deps, user_id, "FileBot", "ghcr.io/hkuds/nanobot:latest")
    result = await mcp_update_agent_file(fleet_deps, UUID(agent["id"]), "SOUL.md", "You are FileBot.")
    assert result["path"] == "SOUL.md"


def _proc():
    p = AsyncMock()
    p.returncode = 0
    p.communicate = AsyncMock(return_value=(b"", b""))
    return p


async def test_mcp_start_stop_agent(mcp_conn_user, fleet_deps):
    conn, user_id = mcp_conn_user
    agent = await mcp_create_agent(fleet_deps, user_id, "StatusBot", "ghcr.io/hkuds/nanobot:latest")
    agent_id = UUID(agent["id"])

    with patch("src.fleet.app.sandbox.asyncio.create_subprocess_exec", return_value=_proc()), \
         patch("src.fleet.app.sandbox.Path.mkdir"), \
         patch("src.fleet.app.sandbox._wait_for_gateway", new_callable=AsyncMock), \
         patch("builtins.open", MagicMock()):
        started = await mcp_start_agent(fleet_deps, agent_id)
    assert started["status"] == "running"

    with patch("src.fleet.app.sandbox.asyncio.create_subprocess_exec", return_value=_proc()), \
         patch("src.fleet.app.sandbox.shutil.rmtree"):
        stopped = await mcp_stop_agent(fleet_deps, agent_id)
    assert stopped["status"] == "idle"


async def test_mcp_delete_agent(mcp_conn_user, fleet_deps):
    conn, user_id = mcp_conn_user
    agent = await mcp_create_agent(fleet_deps, user_id, "DeleteMe", "ghcr.io/hkuds/nanobot:latest")
    agent_id = UUID(agent["id"])

    result = await mcp_delete_agent(fleet_deps, agent_id)
    assert result["deleted"] == str(agent_id)

    agents = await mcp_list_agents(fleet_deps, user_id)
    assert not any(a["id"] == str(agent_id) for a in agents)


async def test_mcp_delete_admin_agent_raises(mcp_conn_user, fleet_deps):
    conn, user_id = mcp_conn_user
    agents = await mcp_list_agents(fleet_deps, user_id)
    admin_id = UUID(next(a["id"] for a in agents if a["is_admin"]))
    with pytest.raises(ValueError, match="Cannot delete the Admin agent"):
        await mcp_delete_agent(fleet_deps, admin_id)


async def test_mcp_create_and_list_skills(mcp_conn_user, library_deps):
    conn, user_id = mcp_conn_user
    result = await mcp_create_skill(library_deps, user_id, "research", "Web research")
    assert result["name"] == "research"
    skills = await mcp_list_skills(library_deps, user_id)
    assert any(s["name"] == "research" for s in skills)


async def test_mcp_attach_skill(mcp_conn_user, fleet_deps, library_deps, integrations_deps):
    conn, user_id = mcp_conn_user
    agent = await mcp_create_agent(fleet_deps, user_id, "SkillBot", "ghcr.io/hkuds/nanobot:latest")
    skill = await mcp_create_skill(library_deps, user_id, "calc", "Calculator")
    result = await mcp_attach_skill(integrations_deps, UUID(agent["id"]), UUID(skill["id"]))
    assert result["attached"] is True
    linked = await integrations_deps.list_agent_skills(UUID(agent["id"]))
    assert any(str(r["id"]) == skill["id"] for r in linked)


async def test_mcp_create_and_list_envs(mcp_conn_user, integrations_deps):
    conn, user_id = mcp_conn_user
    values_json = json.dumps({"OPENAI_API_KEY": "sk-test"})
    result = await mcp_create_env(integrations_deps, user_id, "openai", values_json)
    assert result["name"] == "openai"
    envs = await mcp_list_envs(integrations_deps, user_id)
    assert any(e["name"] == "openai" for e in envs)


async def test_mcp_list_channels(mcp_conn_user, integrations_deps, client):
    conn, user_id = mcp_conn_user
    await client.post(
        "/channels",
        json={"user_id": str(user_id), "type": "telegram", "config": {"token": "bot:abc", "allow_from": []}},
    )
    channels = await mcp_list_channels(integrations_deps, user_id)
    assert any(c["type"] == "telegram" for c in channels)
