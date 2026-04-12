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

Fleet configuration tools. Nanobot exposes them with the prefix `mcp_officeclaw_`:

### Agents
- `mcp_officeclaw_get_fleet_status` — list all agents with idle/running/error counts
- `mcp_officeclaw_create_agent(name, image?)` — create a new agent

### Skills
- `mcp_officeclaw_list_skills` — list skills in your library
- `mcp_officeclaw_create_skill(name, description?)` — create a new skill (auto-creates SKILL.md)
- `mcp_officeclaw_add_skill_file(skill_id, path, content)` — add or update a file in a skill
- `mcp_officeclaw_attach_skill(agent_id, skill_id)` — attach skill to agent

### Env configs
- `mcp_officeclaw_list_envs` — list env configs (values never returned)
- `mcp_officeclaw_create_env(name, values_json)` — create env (values_json is a JSON object string)
- `mcp_officeclaw_attach_env(agent_id, env_id)` — attach env config to agent

### Channels
- `mcp_officeclaw_list_channels` — list channel integrations
- `mcp_officeclaw_create_channel(channel_type, config_json)` — create channel (telegram/discord/whatsapp)
- `mcp_officeclaw_attach_channel(agent_id, channel_id)` — attach channel to agent

### MCP servers
- `mcp_officeclaw_list_mcp_servers` — list user MCP server configs
- `mcp_officeclaw_create_mcp_server(name, server_type, config_json)` — create MCP server (http/stdio)
- `mcp_officeclaw_attach_mcp_server(agent_id, mcp_id)` — attach MCP server to agent

### Templates
- `mcp_officeclaw_list_templates` — list user templates
- `mcp_officeclaw_create_template(name, template_type, content)` — create template (soul/agents/heartbeat/tools/user)
- `mcp_officeclaw_attach_template(agent_id, template_id)` — attach template to agent
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
