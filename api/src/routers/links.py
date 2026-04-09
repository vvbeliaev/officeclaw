from uuid import UUID
from fastapi import APIRouter, Depends
import asyncpg
from src.db.pool import get_pool
from src.models.skill import SkillOut
from src.models.env import EnvOut
from src.models.channel import ChannelOut
from src.models.mcp import McpCreate, McpOut
from src.repositories.links import LinkRepo
from src.repositories.mcp import AgentMcpRepo

router = APIRouter(prefix="/agents/{agent_id}")


def get_link_repo(pool: asyncpg.Connection = Depends(get_pool)) -> LinkRepo:
    return LinkRepo(pool)


def get_mcp_repo(pool: asyncpg.Connection = Depends(get_pool)) -> AgentMcpRepo:
    return AgentMcpRepo(pool)


@router.post("/skills/{skill_id}", status_code=204)
async def attach_skill(
    agent_id: UUID, skill_id: UUID, repo: LinkRepo = Depends(get_link_repo)
) -> None:
    await repo.attach_skill(agent_id, skill_id)


@router.delete("/skills/{skill_id}", status_code=204)
async def detach_skill(
    agent_id: UUID, skill_id: UUID, repo: LinkRepo = Depends(get_link_repo)
) -> None:
    await repo.detach_skill(agent_id, skill_id)


@router.get("/skills", response_model=list[SkillOut])
async def list_agent_skills(
    agent_id: UUID, repo: LinkRepo = Depends(get_link_repo)
) -> list[SkillOut]:
    return [SkillOut(**dict(r)) for r in await repo.list_skills(agent_id)]


@router.post("/envs/{env_id}", status_code=204)
async def attach_env(
    agent_id: UUID, env_id: UUID, repo: LinkRepo = Depends(get_link_repo)
) -> None:
    await repo.attach_env(agent_id, env_id)


@router.delete("/envs/{env_id}", status_code=204)
async def detach_env(
    agent_id: UUID, env_id: UUID, repo: LinkRepo = Depends(get_link_repo)
) -> None:
    await repo.detach_env(agent_id, env_id)


@router.get("/envs", response_model=list[EnvOut])
async def list_agent_envs(
    agent_id: UUID, repo: LinkRepo = Depends(get_link_repo)
) -> list[EnvOut]:
    return [EnvOut(**dict(r)) for r in await repo.list_envs(agent_id)]


@router.post("/channels/{channel_id}", status_code=204)
async def attach_channel(
    agent_id: UUID, channel_id: UUID, repo: LinkRepo = Depends(get_link_repo)
) -> None:
    await repo.attach_channel(agent_id, channel_id)


@router.delete("/channels/{channel_id}", status_code=204)
async def detach_channel(
    agent_id: UUID, channel_id: UUID, repo: LinkRepo = Depends(get_link_repo)
) -> None:
    await repo.detach_channel(agent_id, channel_id)


@router.get("/channels", response_model=list[ChannelOut])
async def list_agent_channels(
    agent_id: UUID, repo: LinkRepo = Depends(get_link_repo)
) -> list[ChannelOut]:
    return [ChannelOut(**dict(r)) for r in await repo.list_channels(agent_id)]


@router.post("/mcp", response_model=McpOut, status_code=201)
async def add_mcp(
    agent_id: UUID, body: McpCreate, repo: AgentMcpRepo = Depends(get_mcp_repo)
) -> McpOut:
    return McpOut(**dict(await repo.create(agent_id, body.name, body.config)))


@router.get("/mcp", response_model=list[McpOut])
async def list_mcp(
    agent_id: UUID, repo: AgentMcpRepo = Depends(get_mcp_repo)
) -> list[McpOut]:
    return [McpOut(**dict(r)) for r in await repo.list_by_agent(agent_id)]
