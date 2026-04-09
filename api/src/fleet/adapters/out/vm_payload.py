# api/src/ports/sandbox/vm_payload.py
"""
Assembles the payload sent to sandbox-manager POST /sandbox/create.

Output shape:
{
  "files": [{"path": str, "content": str}],
  "env":   {KEY: VALUE},           # injected as VM env vars
  "config_json": str,              # nanobot config.json content
}
"""
import json
import logging
from uuid import UUID
import asyncpg
from src.fleet.adapters.out.repository import AgentFileRepo
from src.integrations.adapters.out.repository import (
    LinkRepo,
    EnvRepo,
    ChannelRepo,
    AgentMcpRepo,
)
from src.library.adapters.out.repository import SkillFileRepo

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "anthropic/claude-sonnet-4-6"


async def build_vm_payload(conn: asyncpg.Pool, agent_id: UUID) -> dict:
    file_repo = AgentFileRepo(conn)
    link_repo = LinkRepo(conn)
    env_repo = EnvRepo(conn)
    channel_repo = ChannelRepo(conn)
    mcp_repo = AgentMcpRepo(conn)
    skill_file_repo = SkillFileRepo(conn)

    # 1. Agent workspace files
    files: list[dict] = []
    for rec in await file_repo.list_by_agent(agent_id):
        files.append({"path": rec["path"], "content": rec["content"]})

    # 2. Linked skill files → skills/<name>/
    for skill_rec in await link_repo.list_skills(agent_id):
        skill_name = skill_rec["name"]
        for sf in await skill_file_repo.list_by_skill(skill_rec["id"]):
            files.append(
                {
                    "path": f"skills/{skill_name}/{sf['path']}",
                    "content": sf["content"],
                }
            )

    # 3. Merged env vars from all linked envs
    env_vars: dict = {}
    for env_rec in await link_repo.list_envs(agent_id):
        values = await env_repo.get_decrypted_values(env_rec["id"])
        collisions = set(values) & set(env_vars)
        if collisions:
            logger.warning(
                "Agent %s: env key collision from env %s — overwriting keys: %s",
                agent_id,
                env_rec["id"],
                collisions,
            )
        env_vars = {**env_vars, **values}

    # 4. Build config.json
    config, extra_env = await _build_config_json(
        agent_id, link_repo, env_vars, channel_repo, mcp_repo
    )
    merged_env = {**env_vars, **extra_env}

    return {
        "files": files,
        "env": merged_env,
        "config_json": json.dumps(config, indent=2),
    }


async def _build_config_json(
    agent_id: UUID,
    link_repo: LinkRepo,
    env_vars: dict,
    channel_repo: ChannelRepo,
    mcp_repo: AgentMcpRepo,
) -> tuple[dict, dict]:
    # Providers: one entry per known key prefix found in env_vars
    providers: dict = {}
    if any(k.startswith("ANTHROPIC") for k in env_vars):
        providers["anthropic"] = {"apiKey": "${ANTHROPIC_API_KEY}"}
    if any(k.startswith("OPENAI") for k in env_vars):
        providers["openai"] = {"apiKey": "${OPENAI_API_KEY}"}
    if any(k.startswith("OPENROUTER") for k in env_vars):
        providers["openrouter"] = {"apiKey": "${OPENROUTER_API_KEY}"}
    if any(k.startswith("GROQ") for k in env_vars):
        providers["groq"] = {"apiKey": "${GROQ_API_KEY}"}

    # Channels
    extra_env: dict = {}
    channels_config: dict = {"sendProgress": True}
    for ch_rec in await link_repo.list_channels(agent_id):
        cfg = await channel_repo.get_decrypted_config(ch_rec["id"])
        ch_type = ch_rec["type"]
        if ch_type == "telegram":
            token_key = "TELEGRAM_TOKEN"
            extra_env.setdefault(token_key, cfg.get("token", ""))
            channels_config["telegram"] = {
                "enabled": True,
                "token": f"${{{token_key}}}",
                "allowFrom": cfg.get("allow_from", []),
            }
        elif ch_type == "discord":
            token_key = "DISCORD_TOKEN"
            extra_env.setdefault(token_key, cfg.get("token", ""))
            channels_config["discord"] = {
                "enabled": True,
                "token": f"${{{token_key}}}",
                "allowFrom": cfg.get("allow_from", []),
            }

    # MCP servers
    mcp_servers: dict = {}
    for mcp in await mcp_repo.get_all_decrypted(agent_id):
        mcp_servers[mcp["name"]] = mcp["config"]

    config_dict = {
        "agents": {
            "defaults": {
                "workspace": "/workspace",
                "model": _DEFAULT_MODEL,
            }
        },
        "providers": providers,
        "channels": channels_config,
        "tools": {
            "exec": {"enable": True},
            "mcpServers": mcp_servers,
        },
        "gateway": {"host": "0.0.0.0", "port": 18790},
    }
    return config_dict, extra_env
