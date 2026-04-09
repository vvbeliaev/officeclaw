from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
import asyncpg
from src.shared.db.pool import get_pool
from src.integrations.core.schema import EnvCreate, EnvOut, ChannelCreate, ChannelOut, McpCreate, McpOut
from src.integrations.adapters.outbound.repository import EnvRepo, ChannelRepo, LinkRepo, AgentMcpRepo
from src.library.core.schema import SkillOut

envs_router = APIRouter()
channels_router = APIRouter()
links_router = APIRouter(prefix="/agents/{agent_id}")


def get_env_repo(pool: asyncpg.Connection = Depends(get_pool)) -> EnvRepo:
    return EnvRepo(pool)


def get_channel_repo(pool: asyncpg.Connection = Depends(get_pool)) -> ChannelRepo:
    return ChannelRepo(pool)


def get_link_repo(pool: asyncpg.Connection = Depends(get_pool)) -> LinkRepo:
    return LinkRepo(pool)


def get_mcp_repo(pool: asyncpg.Connection = Depends(get_pool)) -> AgentMcpRepo:
    return AgentMcpRepo(pool)


@envs_router.post("", response_model=EnvOut, status_code=201)
async def create_env(body: EnvCreate, repo: EnvRepo = Depends(get_env_repo)) -> EnvOut:
    try:
        record = await repo.create(body.user_id, body.name, body.values)
    except asyncpg.UniqueViolationError:
        raise HTTPException(409, "Env name already exists for this user")
    return EnvOut(**dict(record))


@envs_router.get("", response_model=list[EnvOut])
async def list_envs(user_id: UUID, repo: EnvRepo = Depends(get_env_repo)) -> list[EnvOut]:
    return [EnvOut(**dict(r)) for r in await repo.list_by_user(user_id)]


@envs_router.delete("/{env_id}", status_code=204)
async def delete_env(env_id: UUID, repo: EnvRepo = Depends(get_env_repo)) -> None:
    if not await repo.find_by_id(env_id):
        raise HTTPException(404, "Env not found")
    await repo.delete(env_id)


@channels_router.post("", response_model=ChannelOut, status_code=201)
async def create_channel(body: ChannelCreate, repo: ChannelRepo = Depends(get_channel_repo)) -> ChannelOut:
    record = await repo.create(body.user_id, body.type, body.config)
    return ChannelOut(**dict(record))


@channels_router.get("", response_model=list[ChannelOut])
async def list_channels(user_id: UUID, repo: ChannelRepo = Depends(get_channel_repo)) -> list[ChannelOut]:
    return [ChannelOut(**dict(r)) for r in await repo.list_by_user(user_id)]


@channels_router.delete("/{channel_id}", status_code=204)
async def delete_channel(channel_id: UUID, repo: ChannelRepo = Depends(get_channel_repo)) -> None:
    if not await repo.find_by_id(channel_id):
        raise HTTPException(404, "Channel not found")
    await repo.delete(channel_id)


@links_router.post("/skills/{skill_id}", status_code=204)
async def attach_skill(
    agent_id: UUID, skill_id: UUID, repo: LinkRepo = Depends(get_link_repo)
) -> None:
    await repo.attach_skill(agent_id, skill_id)


@links_router.delete("/skills/{skill_id}", status_code=204)
async def detach_skill(
    agent_id: UUID, skill_id: UUID, repo: LinkRepo = Depends(get_link_repo)
) -> None:
    await repo.detach_skill(agent_id, skill_id)


@links_router.get("/skills", response_model=list[SkillOut])
async def list_agent_skills(
    agent_id: UUID, repo: LinkRepo = Depends(get_link_repo)
) -> list[SkillOut]:
    return [SkillOut(**dict(r)) for r in await repo.list_skills(agent_id)]


@links_router.post("/envs/{env_id}", status_code=204)
async def attach_env(
    agent_id: UUID, env_id: UUID, repo: LinkRepo = Depends(get_link_repo)
) -> None:
    await repo.attach_env(agent_id, env_id)


@links_router.delete("/envs/{env_id}", status_code=204)
async def detach_env(
    agent_id: UUID, env_id: UUID, repo: LinkRepo = Depends(get_link_repo)
) -> None:
    await repo.detach_env(agent_id, env_id)


@links_router.get("/envs", response_model=list[EnvOut])
async def list_agent_envs(
    agent_id: UUID, repo: LinkRepo = Depends(get_link_repo)
) -> list[EnvOut]:
    return [EnvOut(**dict(r)) for r in await repo.list_envs(agent_id)]


@links_router.post("/channels/{channel_id}", status_code=204)
async def attach_channel(
    agent_id: UUID, channel_id: UUID, repo: LinkRepo = Depends(get_link_repo)
) -> None:
    await repo.attach_channel(agent_id, channel_id)


@links_router.delete("/channels/{channel_id}", status_code=204)
async def detach_channel(
    agent_id: UUID, channel_id: UUID, repo: LinkRepo = Depends(get_link_repo)
) -> None:
    await repo.detach_channel(agent_id, channel_id)


@links_router.get("/channels", response_model=list[ChannelOut])
async def list_agent_channels(
    agent_id: UUID, repo: LinkRepo = Depends(get_link_repo)
) -> list[ChannelOut]:
    return [ChannelOut(**dict(r)) for r in await repo.list_channels(agent_id)]


@links_router.post("/mcp", response_model=McpOut, status_code=201)
async def add_mcp(
    agent_id: UUID, body: McpCreate, repo: AgentMcpRepo = Depends(get_mcp_repo)
) -> McpOut:
    return McpOut(**dict(await repo.create(agent_id, body.name, body.config)))


@links_router.get("/mcp", response_model=list[McpOut])
async def list_mcp(
    agent_id: UUID, repo: AgentMcpRepo = Depends(get_mcp_repo)
) -> list[McpOut]:
    return [McpOut(**dict(r)) for r in await repo.list_by_agent(agent_id)]
