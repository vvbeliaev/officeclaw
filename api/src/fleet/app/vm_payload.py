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

from src.fleet.app.agents import AgentService
from src.integrations.app import IntegrationsApp
from src.library.app import LibraryApp
from src.shared.config import get_settings

logger = logging.getLogger(__name__)

# Fallback model string burned into config.json if a user env override
# is absent. nanobot resolves ${OFFICECLAW_LLM_MODEL} from the sandbox
# env vars; see _build_config_json below.
_FALLBACK_MODEL = "${OFFICECLAW_LLM_MODEL}"

# Maps template_type to the nanobot runtime filename it controls.
# When a user_template of a given type is attached to an agent, its content
# is prepended to the corresponding agent file (separated by "---").
_RUNTIME_FILES: dict[str, str] = {
    "user":      "USER.md",
    "soul":      "SOUL.md",
    "agents":    "AGENTS.md",
    "heartbeat": "HEARTBEAT.md",
    "tools":     "TOOLS.md",
}


async def build_vm_payload(
    agent_id: UUID,
    agents: AgentService,
    integrations: IntegrationsApp,
    skills: LibraryApp,
) -> dict:
    # 1. Agent workspace files — split runtime files from regular files
    files: list[dict] = []
    agent_runtime: dict[str, str] = {}  # path → content for the 5 runtime file types
    runtime_paths = set(_RUNTIME_FILES.values())

    for rec in await agents.list_files(agent_id):
        if rec["path"] in runtime_paths:
            agent_runtime[rec["path"]] = rec["content"]
        else:
            files.append({"path": rec["path"], "content": rec["content"]})

    # 1b. Attached user_templates → prepend to the matching runtime file.
    #     template content + "\n---\n" + agent override (either part may be absent).
    attached_templates = await integrations.list_agent_templates(agent_id)
    template_by_type: dict[str, str] = {
        t["template_type"]: t["content"] for t in attached_templates
    }

    for ttype, path in _RUNTIME_FILES.items():
        tpl = template_by_type.get(ttype)
        override = agent_runtime.get(path)
        if tpl and override:
            content = tpl + "\n---\n" + override
        elif tpl:
            content = tpl
        elif override:
            content = override
        else:
            continue
        files.append({"path": path, "content": content})

    # 2. Linked skill files → skills/<name>/
    for skill_rec in await integrations.list_agent_skills(agent_id):
        skill_name = skill_rec["name"]
        for sf in await skills.list_files(skill_rec["id"]):
            files.append(
                {
                    "path": f"skills/{skill_name}/{sf['path']}",
                    "content": sf["content"],
                }
            )

    # 3. Merged env vars from all linked envs
    env_vars: dict = {}
    for env_rec in await integrations.list_agent_envs(agent_id):
        values = await integrations.get_decrypted_env(env_rec["id"])
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
    config, extra_env = await _build_config_json(agent_id, integrations, env_vars)
    merged_env = {**env_vars, **extra_env}

    return {
        "files": files,
        "env": merged_env,
        "config_json": json.dumps(config, indent=2),
    }


async def _build_config_json(
    agent_id: UUID,
    integrations: IntegrationsApp,
    env_vars: dict,
) -> tuple[dict, dict]:
    # Single OpenAI-compatible provider slot. nanobot's `custom` entry in
    # the provider registry is a direct OpenAI-compat client — we force
    # it via `agents.defaults.provider = "custom"` so the match bypasses
    # keyword-based resolution entirely. Actual values live in env vars
    # so secrets never touch config.json on disk.
    providers: dict = {
        "custom": {
            "api_key": "${OFFICECLAW_LLM_API_KEY}",
            "api_base": "${OFFICECLAW_LLM_BASE_URL}",
        }
    }

    # Channels
    extra_env: dict = {}
    channels_config: dict = {"sendProgress": True}
    for ch_rec in await integrations.list_agent_channels(agent_id):
        cfg = await integrations.get_decrypted_channel(ch_rec["id"])
        ch_type = ch_rec["type"]
        if ch_type == "telegram":
            token_key = "TELEGRAM_TOKEN"
            extra_env.setdefault(token_key, cfg.get("token", ""))
            tg: dict = {
                "enabled": True,
                "token": f"${{{token_key}}}",
                "allowFrom": cfg.get("allow_from", ["*"]),
            }
            if cfg.get("operators"):
                tg["operators"] = cfg["operators"]
            if cfg.get("streaming") is not None:
                tg["streaming"] = cfg["streaming"]
            if cfg.get("proxy"):
                tg["proxy"] = cfg["proxy"]
            if cfg.get("group_policy"):
                tg["groupPolicy"] = cfg["group_policy"]
            if cfg.get("react_emoji"):
                tg["reactEmoji"] = cfg["react_emoji"]
            channels_config["telegram"] = tg
        elif ch_type == "discord":
            token_key = "DISCORD_TOKEN"
            extra_env.setdefault(token_key, cfg.get("token", ""))
            channels_config["discord"] = {
                "enabled": True,
                "token": f"${{{token_key}}}",
                "allowFrom": cfg.get("allow_from", ["*"]),
            }
        elif ch_type == "whatsapp":
            bridge_token_key = "WHATSAPP_BRIDGE_TOKEN"
            extra_env.setdefault(bridge_token_key, cfg.get("bridge_token", ""))
            channels_config["whatsapp"] = {
                "enabled": True,
                "bridgeUrl": cfg.get("bridge_url", "ws://localhost:3001"),
                "bridgeToken": f"${{{bridge_token_key}}}",
                "allowFrom": cfg.get("allow_from", ["*"]),
            }

    # Ensure LLM vars are present — fall back to server-wide defaults if the
    # agent's linked envs didn't supply them (e.g. bootstrapped before defaults
    # were configured, or user wiped the default-llm env).
    settings = get_settings()
    llm_defaults = {
        "OFFICECLAW_LLM_API_KEY": settings.default_llm_api_key,
        "OFFICECLAW_LLM_BASE_URL": settings.default_llm_base_url,
        "OFFICECLAW_LLM_MODEL": settings.default_llm_model,
    }
    for key, val in llm_defaults.items():
        if not env_vars.get(key) and val:
            extra_env[key] = val

    # MCP URL is injected at VM-start time (not burned in at bootstrap) so that
    # the correct hostname is always used — e.g. host.docker.internal for local
    # Docker dev vs a real hostname in production.
    extra_env["OFFICECLAW_MCP_URL"] = f"{settings.mcp_base_url}/mcp/"

    # MCP servers
    mcp_servers: dict = {}
    for mcp in await integrations.get_all_decrypted_mcp(agent_id):
        mcp_servers[mcp["name"]] = mcp["config"]

    config_dict = {
        "agents": {
            "defaults": {
                "workspace": "/workspace",
                "model": _FALLBACK_MODEL,
                "provider": "custom",
                "dream": {
                    "intervalH": 2,
                    "maxBatchSize": 20,
                    "maxIterations": 10,
                },
            }
        },
        "providers": providers,
        "channels": channels_config,
        "tools": {
            "exec": {"enable": True},
            "mcpServers": mcp_servers,
        },
        "gateway": {
            "host": "0.0.0.0",
            "port": 18790,
            "heartbeat": {"enabled": True, "intervalS": 1800},
        },
    }
    return config_dict, extra_env
