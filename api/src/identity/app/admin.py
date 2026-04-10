# api/src/identity/service.py
"""
Admin agent bootstrap -- runs at user registration.

Creates:
  1. OFFICECLAW_TOKEN stored in users.officeclaw_token
  2. user_envs row: name='officeclaw', values={OFFICECLAW_TOKEN: token}
  3. agents row: name='Admin', is_admin=True
  4. agent_files: SOUL.md, AGENTS.md, TOOLS.md
  5. user_mcp row: name='officeclaw', type='http', config with url + auth header
  6. agent_mcp link: admin agent <-> officeclaw mcp
  7. agent_envs link: admin agent <- officeclaw env
"""
import secrets
from uuid import UUID

import asyncpg

from src.shared.config import get_settings
from src.fleet.adapters.out.repository import AgentRepo
from src.fleet.adapters.out.repository import AgentFileRepo
from src.integrations.adapters.out.repository import EnvRepo
from src.integrations.adapters.out.repository import LinkRepo
from src.integrations.adapters.out.repository import UserMcpRepo
from src.identity.adapters.out.repository import UserRepo

_SOUL_MD = """
You are the Admin agent for OfficeClaw -- a fleet manager AI that helps users
create, configure, and manage their personal AI agents.

You have access to the `officeclaw` MCP tool which allows you to perform all
fleet operations: creating agents, installing skills, configuring channels,
managing environment variables, and monitoring fleet status.

When the user asks you to do something with their agents, use the officeclaw
tools to make it happen. Be proactive and helpful. When creating agents,
suggest good names and configurations. When installing skills, explain what
the skill does.

Always confirm important actions (deleting agents, changing configurations)
before executing them.
"""

_AGENTS_MD = """
# Agents

You operate as a fleet manager. Your job is to help the user build and manage
their fleet of AI agents.

## Available MCP Tools
- officeclaw: Fleet management (create/start/stop/delete agents, manage skills, envs, channels)
"""

_TOOLS_MD = """
# Tools

## officeclaw MCP

Fleet management tool. Use it to:
- List agents: `list_agents`
- Create an agent: `create_agent(name, image?)`
- Start/stop an agent: `start_agent(agent_id)`, `stop_agent(agent_id)`
- Update files: `update_agent_file(agent_id, path, content)`
- Delete an agent: `delete_agent(agent_id)`
- Skills: `list_skills`, `create_skill(name, description?)`, `attach_skill(agent_id, skill_id)`
- Envs: `list_envs`, `create_env(name, values_json)`
- Channels: `list_channels`
- Fleet status: `get_fleet_status`
"""


async def create_admin_for_user(conn: asyncpg.Pool, user_id: UUID) -> str:
    """
    Bootstrap the Admin agent for a newly registered user.
    Returns the plain-text OFFICECLAW_TOKEN (show once to the user).

    Uses conn directly -- compatible with both asyncpg.Pool and asyncpg.Connection
    (same pattern as all other repos in this codebase).
    """
    token = secrets.token_urlsafe(32)
    settings = get_settings()

    users_repo = UserRepo(conn)
    agents_repo = AgentRepo(conn)
    files_repo = AgentFileRepo(conn)
    envs_repo = EnvRepo(conn)
    links_repo = LinkRepo(conn)
    mcp_repo = UserMcpRepo(conn)

    await users_repo.set_token(user_id, token)

    env_record = await envs_repo.create(
        user_id, "officeclaw", {"OFFICECLAW_TOKEN": token}
    )

    agent_record = await agents_repo.create(
        user_id,
        "Admin",
        "localhost:5005/officeclaw/agent:latest",
        True,
    )
    agent_id = agent_record["id"]

    await files_repo.upsert(agent_id, "SOUL.md", _SOUL_MD)
    await files_repo.upsert(agent_id, "AGENTS.md", _AGENTS_MD)
    await files_repo.upsert(agent_id, "TOOLS.md", _TOOLS_MD)

    mcp_record = await mcp_repo.create(
        user_id,
        "officeclaw",
        "http",
        {
            "url": "${OFFICECLAW_MCP_URL}",
            "headers": {"Authorization": "Bearer ${OFFICECLAW_TOKEN}"},
        },
    )

    await links_repo.attach_mcp(agent_id, mcp_record["id"])
    await links_repo.attach_env(agent_id, env_record["id"])

    return token
