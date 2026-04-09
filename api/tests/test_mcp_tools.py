# api/tests/test_mcp_tools.py
from uuid import UUID


async def test_mcp_list_agents(mcp_conn_user):
    from src.adapters.mcp.server import mcp_list_agents
    conn, user_id = mcp_conn_user
    agents = await mcp_list_agents(conn, user_id)
    # Admin agent was created by registration
    assert any(a["name"] == "Admin" for a in agents)


async def test_mcp_get_fleet_status(mcp_conn_user):
    from src.adapters.mcp.server import mcp_get_fleet_status
    conn, user_id = mcp_conn_user
    status = await mcp_get_fleet_status(conn, user_id)
    assert "agents" in status
    assert "summary" in status
    assert set(status["summary"].keys()) == {"idle", "running", "error"}


async def test_mcp_create_agent(mcp_conn_user):
    from src.adapters.mcp.server import mcp_create_agent
    conn, user_id = mcp_conn_user
    result = await mcp_create_agent(conn, user_id, "MyBot", "ghcr.io/hkuds/nanobot:latest")
    assert result["name"] == "MyBot"
    assert result["status"] == "idle"
    assert "id" in result


async def test_mcp_update_agent_file(mcp_conn_user):
    from src.adapters.mcp.server import mcp_create_agent, mcp_update_agent_file
    conn, user_id = mcp_conn_user
    agent = await mcp_create_agent(conn, user_id, "FileBot", "ghcr.io/hkuds/nanobot:latest")
    result = await mcp_update_agent_file(conn, UUID(agent["id"]), "SOUL.md", "You are FileBot.")
    assert result["path"] == "SOUL.md"


async def test_mcp_start_stop_agent(mcp_conn_user):
    from src.adapters.mcp.server import mcp_create_agent, mcp_start_agent, mcp_stop_agent
    from unittest.mock import AsyncMock, MagicMock, patch
    conn, user_id = mcp_conn_user

    def _proc():
        p = AsyncMock()
        p.returncode = 0
        p.communicate = AsyncMock(return_value=(b"", b""))
        return p

    agent = await mcp_create_agent(conn, user_id, "StatusBot", "ghcr.io/hkuds/nanobot:latest")
    agent_id = UUID(agent["id"])

    with patch("src.fleet.service.asyncio.create_subprocess_exec", return_value=_proc()), \
         patch("src.fleet.service.Path.mkdir"), \
         patch("builtins.open", MagicMock()):
        started = await mcp_start_agent(conn, agent_id)
    assert started["status"] == "running"

    with patch("src.fleet.service.asyncio.create_subprocess_exec", return_value=_proc()), \
         patch("src.fleet.service.shutil.rmtree"):
        stopped = await mcp_stop_agent(conn, agent_id)
    assert stopped["status"] == "idle"


async def test_mcp_delete_agent(mcp_conn_user):
    from src.adapters.mcp.server import mcp_create_agent, mcp_delete_agent, mcp_list_agents
    conn, user_id = mcp_conn_user
    agent = await mcp_create_agent(conn, user_id, "DeleteMe", "ghcr.io/hkuds/nanobot:latest")
    agent_id = UUID(agent["id"])

    result = await mcp_delete_agent(conn, agent_id)
    assert result["deleted"] == str(agent_id)

    agents = await mcp_list_agents(conn, user_id)
    assert not any(a["id"] == str(agent_id) for a in agents)


async def test_mcp_delete_admin_agent_raises(mcp_conn_user):
    from src.adapters.mcp.server import mcp_list_agents, mcp_delete_agent
    import pytest
    conn, user_id = mcp_conn_user
    agents = await mcp_list_agents(conn, user_id)
    admin_id = UUID(next(a["id"] for a in agents if a["is_admin"]))
    with pytest.raises(ValueError, match="Cannot delete the Admin agent"):
        await mcp_delete_agent(conn, admin_id)


async def test_mcp_create_and_list_skills(mcp_conn_user):
    from src.adapters.mcp.server import mcp_create_skill, mcp_list_skills
    conn, user_id = mcp_conn_user
    result = await mcp_create_skill(conn, user_id, "research", "Web research")
    assert result["name"] == "research"
    skills = await mcp_list_skills(conn, user_id)
    assert any(s["name"] == "research" for s in skills)


async def test_mcp_attach_skill(mcp_conn_user):
    from src.adapters.mcp.server import mcp_create_agent, mcp_create_skill, mcp_attach_skill
    from src.integrations.repository import LinkRepo
    conn, user_id = mcp_conn_user
    agent = await mcp_create_agent(conn, user_id, "SkillBot", "ghcr.io/hkuds/nanobot:latest")
    skill = await mcp_create_skill(conn, user_id, "calc", "Calculator")
    result = await mcp_attach_skill(conn, UUID(agent["id"]), UUID(skill["id"]))
    assert result["attached"] is True
    linked = await LinkRepo(conn).list_skills(UUID(agent["id"]))
    assert any(str(r["id"]) == skill["id"] for r in linked)


async def test_mcp_create_and_list_envs(mcp_conn_user):
    from src.adapters.mcp.server import mcp_create_env, mcp_list_envs
    import json
    conn, user_id = mcp_conn_user
    values_json = json.dumps({"OPENAI_API_KEY": "sk-test"})
    result = await mcp_create_env(conn, user_id, "openai", values_json)
    assert result["name"] == "openai"
    envs = await mcp_list_envs(conn, user_id)
    # includes the 'officeclaw' env created at registration + new 'openai'
    assert any(e["name"] == "openai" for e in envs)


async def test_mcp_list_channels(mcp_conn_user, client):
    from src.adapters.mcp.server import mcp_list_channels
    conn, user_id = mcp_conn_user
    # Create a channel via REST to have something to list
    await client.post("/channels", json={
        "user_id": str(user_id),
        "type": "telegram",
        "config": {"token": "bot:abc", "allow_from": []}
    })
    channels = await mcp_list_channels(conn, user_id)
    assert any(c["type"] == "telegram" for c in channels)
