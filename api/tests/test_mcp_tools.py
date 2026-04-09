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
