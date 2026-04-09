from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Request

from src.integrations.app import IntegrationsApp
from src.integrations.core.schema import (
    ChannelCreate, ChannelOut,
    EnvCreate, EnvOut,
    McpCreate, McpOut,
)

envs_router = APIRouter()
channels_router = APIRouter()
links_router = APIRouter(prefix="/agents/{agent_id}")


def get_integrations(request: Request) -> IntegrationsApp:
    return request.app.state.integrations


@envs_router.post("", response_model=EnvOut, status_code=201)
async def create_env(
    body: EnvCreate,
    deps: IntegrationsApp = Depends(get_integrations),
) -> EnvOut:
    try:
        record = await deps.create_env(body.user_id, body.name, body.values)
    except asyncpg.UniqueViolationError:
        raise HTTPException(409, "Env name already exists for this user")
    return EnvOut(**dict(record))


@envs_router.delete("/{env_id}", status_code=204)
async def delete_env(
    env_id: UUID,
    deps: IntegrationsApp = Depends(get_integrations),
) -> None:
    if not await deps.find_env(env_id):
        raise HTTPException(404, "Env not found")
    await deps.delete_env(env_id)


@channels_router.post("", response_model=ChannelOut, status_code=201)
async def create_channel(
    body: ChannelCreate,
    deps: IntegrationsApp = Depends(get_integrations),
) -> ChannelOut:
    record = await deps.create_channel(body.user_id, body.type, body.config)
    return ChannelOut(**dict(record))


@channels_router.delete("/{channel_id}", status_code=204)
async def delete_channel(
    channel_id: UUID,
    deps: IntegrationsApp = Depends(get_integrations),
) -> None:
    if not await deps.find_channel(channel_id):
        raise HTTPException(404, "Channel not found")
    await deps.delete_channel(channel_id)


@links_router.post("/skills/{skill_id}", status_code=204)
async def attach_skill(
    agent_id: UUID, skill_id: UUID,
    deps: IntegrationsApp = Depends(get_integrations),
) -> None:
    await deps.attach_skill(agent_id, skill_id)


@links_router.delete("/skills/{skill_id}", status_code=204)
async def detach_skill(
    agent_id: UUID, skill_id: UUID,
    deps: IntegrationsApp = Depends(get_integrations),
) -> None:
    await deps.detach_skill(agent_id, skill_id)


@links_router.post("/envs/{env_id}", status_code=204)
async def attach_env(
    agent_id: UUID, env_id: UUID,
    deps: IntegrationsApp = Depends(get_integrations),
) -> None:
    await deps.attach_env(agent_id, env_id)


@links_router.delete("/envs/{env_id}", status_code=204)
async def detach_env(
    agent_id: UUID, env_id: UUID,
    deps: IntegrationsApp = Depends(get_integrations),
) -> None:
    await deps.detach_env(agent_id, env_id)


@links_router.post("/channels/{channel_id}", status_code=204)
async def attach_channel(
    agent_id: UUID, channel_id: UUID,
    deps: IntegrationsApp = Depends(get_integrations),
) -> None:
    await deps.attach_channel(agent_id, channel_id)


@links_router.delete("/channels/{channel_id}", status_code=204)
async def detach_channel(
    agent_id: UUID, channel_id: UUID,
    deps: IntegrationsApp = Depends(get_integrations),
) -> None:
    await deps.detach_channel(agent_id, channel_id)


@links_router.post("/mcp", response_model=McpOut, status_code=201)
async def add_mcp(
    agent_id: UUID,
    body: McpCreate,
    deps: IntegrationsApp = Depends(get_integrations),
) -> McpOut:
    return McpOut(**dict(await deps.create_mcp(agent_id, body.name, body.config)))
