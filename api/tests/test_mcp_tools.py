# api/tests/test_mcp_tools.py
from uuid import UUID


async def test_mcp_list_agents(mcp_conn_user):
    from src.mcp_server import mcp_list_agents
    conn, user_id = mcp_conn_user
    agents = await mcp_list_agents(conn, user_id)
    # Admin agent was created by registration
    assert any(a["name"] == "Admin" for a in agents)


async def test_mcp_get_fleet_status(mcp_conn_user):
    from src.mcp_server import mcp_get_fleet_status
    conn, user_id = mcp_conn_user
    status = await mcp_get_fleet_status(conn, user_id)
    assert "agents" in status
    assert "summary" in status
    assert set(status["summary"].keys()) == {"idle", "running", "error"}


async def test_mcp_create_agent(mcp_conn_user):
    from src.mcp_server import mcp_create_agent
    conn, user_id = mcp_conn_user
    result = await mcp_create_agent(conn, user_id, "MyBot", "ghcr.io/hkuds/nanobot:latest")
    assert result["name"] == "MyBot"
    assert result["status"] == "idle"
    assert "id" in result


async def test_mcp_update_agent_file(mcp_conn_user):
    from src.mcp_server import mcp_create_agent, mcp_update_agent_file
    conn, user_id = mcp_conn_user
    agent = await mcp_create_agent(conn, user_id, "FileBot", "ghcr.io/hkuds/nanobot:latest")
    result = await mcp_update_agent_file(conn, UUID(agent["id"]), "SOUL.md", "You are FileBot.")
    assert result["path"] == "SOUL.md"


async def test_mcp_start_stop_agent(mcp_conn_user):
    from src.mcp_server import mcp_create_agent, mcp_start_agent, mcp_stop_agent
    conn, user_id = mcp_conn_user
    agent = await mcp_create_agent(conn, user_id, "StatusBot", "ghcr.io/hkuds/nanobot:latest")
    agent_id = UUID(agent["id"])

    started = await mcp_start_agent(conn, agent_id)
    assert started["status"] == "running"

    stopped = await mcp_stop_agent(conn, agent_id)
    assert stopped["status"] == "idle"


async def test_mcp_delete_agent(mcp_conn_user):
    from src.mcp_server import mcp_create_agent, mcp_delete_agent, mcp_list_agents
    conn, user_id = mcp_conn_user
    agent = await mcp_create_agent(conn, user_id, "DeleteMe", "ghcr.io/hkuds/nanobot:latest")
    agent_id = UUID(agent["id"])

    result = await mcp_delete_agent(conn, agent_id)
    assert result["deleted"] == str(agent_id)

    agents = await mcp_list_agents(conn, user_id)
    assert not any(a["id"] == str(agent_id) for a in agents)


async def test_mcp_delete_admin_agent_raises(mcp_conn_user):
    from src.mcp_server import mcp_list_agents, mcp_delete_agent
    import pytest
    conn, user_id = mcp_conn_user
    agents = await mcp_list_agents(conn, user_id)
    admin_id = UUID(next(a["id"] for a in agents if a["is_admin"]))
    with pytest.raises(ValueError, match="Cannot delete the Admin agent"):
        await mcp_delete_agent(conn, admin_id)
