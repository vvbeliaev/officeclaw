# api/tests/test_admin.py
from uuid import UUID

from tests.conftest import register_user


async def test_bootstrap_returns_token(client, conn):
    body = await register_user(client, conn, "admin-test@example.com")
    assert "officeclaw_token" in body
    assert "workspace_id" in body
    assert len(body["officeclaw_token"]) > 20


async def test_bootstrap_creates_admin_agent(client, conn, fleet_deps):
    body = await register_user(client, conn, "admin-agent@example.com")
    workspace_id = UUID(body["workspace_id"])
    agents = await fleet_deps.list_agents(workspace_id)
    admin_agents = [a for a in agents if a["is_admin"]]
    assert len(admin_agents) == 1
    assert admin_agents[0]["name"] == "Admin"


async def test_admin_agent_has_seed_files(client, conn, fleet_deps):
    body = await register_user(client, conn, "admin-files@example.com")
    workspace_id = UUID(body["workspace_id"])
    agents = await fleet_deps.list_agents(workspace_id)
    agent_id = next(a["id"] for a in agents if a["is_admin"])
    files = await fleet_deps.list_files(agent_id)
    paths = {f["path"] for f in files}
    assert "SOUL.md" in paths
    assert "AGENTS.md" in paths
    assert "TOOLS.md" in paths


async def test_admin_agent_has_mcp_config(client, conn, fleet_deps, integrations_deps):
    body = await register_user(client, conn, "admin-mcp@example.com")
    workspace_id = UUID(body["workspace_id"])
    agents = await fleet_deps.list_agents(workspace_id)
    agent_id = next(a["id"] for a in agents if a["is_admin"])
    mcp_list = await integrations_deps.list_agent_mcps(agent_id)
    names = [m["name"] for m in mcp_list]
    assert any("officeclaw" in name for name in names)


async def test_admin_agent_has_env_linked(client, conn, fleet_deps, integrations_deps):
    body = await register_user(client, conn, "admin-env@example.com")
    workspace_id = UUID(body["workspace_id"])
    agents = await fleet_deps.list_agents(workspace_id)
    agent_id = next(a["id"] for a in agents if a["is_admin"])
    envs = await integrations_deps.list_agent_envs(agent_id)
    names = {e["name"] for e in envs}
    # Bootstrap seeds two envs on the Admin agent: default-llm (feeds
    # ${OFFICECLAW_LLM_*}) and default-web-search (feeds ${OFFICECLAW_WEB_SEARCH_*}).
    # The workspace token itself is injected as OFFICECLAW_TOKEN at sandbox
    # start time, not stored in a workspace_envs row.
    assert names == {"default-llm", "default-web-search"}
