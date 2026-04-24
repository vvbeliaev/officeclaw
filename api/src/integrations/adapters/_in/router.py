from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Request

from src.integrations.app import IntegrationsApp
from src.integrations.core.schema import (
    AgentCronUpdate, AgentCronWithCronOut,
    ChannelCreate, ChannelConfigOut, ChannelOut, ChannelUpdate,
    CronCreate, CronOut, CronUpdate,
    EnvCreate, EnvOut, EnvUpdate, EnvValuesOut,
    McpConfigOut, McpCreate, McpOut, McpUpdate,
    TemplateCreate, TemplateOut, TemplateUpdate,
)

envs_router = APIRouter()
channels_router = APIRouter()
mcp_router = APIRouter()
templates_router = APIRouter()
crons_router = APIRouter()
links_router = APIRouter(prefix="/agents/{agent_id}")


def get_integrations(request: Request) -> IntegrationsApp:
    return request.app.state.integrations


@envs_router.post("", response_model=EnvOut, status_code=201)
async def create_env(
    body: EnvCreate,
    deps: IntegrationsApp = Depends(get_integrations),
) -> EnvOut:
    try:
        record = await deps.create_env(body.workspace_id, body.name, body.values, body.category)
    except asyncpg.UniqueViolationError:
        raise HTTPException(409, "Env name already exists for this workspace")
    return EnvOut(**dict(record))


@envs_router.get("/{env_id}/values", response_model=EnvValuesOut)
async def get_env_values(
    env_id: UUID,
    deps: IntegrationsApp = Depends(get_integrations),
) -> EnvValuesOut:
    if not await deps.find_env(env_id):
        raise HTTPException(404, "Env not found")
    values = await deps.get_decrypted_env(env_id)
    return EnvValuesOut(values=values)


@envs_router.patch("/{env_id}", response_model=EnvOut)
async def update_env(
    env_id: UUID,
    body: EnvUpdate,
    deps: IntegrationsApp = Depends(get_integrations),
) -> EnvOut:
    if not await deps.find_env(env_id):
        raise HTTPException(404, "Env not found")
    record = await deps.update_env(env_id, name=body.name, values=body.values, category=body.category)
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
    record = await deps.create_channel(body.workspace_id, body.name, body.type, body.config)
    return ChannelOut(**dict(record))


@channels_router.get("/{channel_id}/config", response_model=ChannelConfigOut)
async def get_channel_config(
    channel_id: UUID,
    deps: IntegrationsApp = Depends(get_integrations),
) -> ChannelConfigOut:
    if not await deps.find_channel(channel_id):
        raise HTTPException(404, "Channel not found")
    config = await deps.get_decrypted_channel(channel_id)
    return ChannelConfigOut(config=config)


@channels_router.patch("/{channel_id}", response_model=ChannelOut)
async def update_channel(
    channel_id: UUID,
    body: ChannelUpdate,
    deps: IntegrationsApp = Depends(get_integrations),
) -> ChannelOut:
    if not await deps.find_channel(channel_id):
        raise HTTPException(404, "Channel not found")
    record = await deps.update_channel(channel_id, name=body.name, config=body.config)
    return ChannelOut(**dict(record))


@channels_router.delete("/{channel_id}", status_code=204)
async def delete_channel(
    channel_id: UUID,
    deps: IntegrationsApp = Depends(get_integrations),
) -> None:
    if not await deps.find_channel(channel_id):
        raise HTTPException(404, "Channel not found")
    await deps.delete_channel(channel_id)


@mcp_router.post("", response_model=McpOut, status_code=201)
async def create_mcp(
    body: McpCreate,
    deps: IntegrationsApp = Depends(get_integrations),
) -> McpOut:
    try:
        record = await deps.create_mcp(body.workspace_id, body.name, body.type, body.config)
    except asyncpg.UniqueViolationError:
        raise HTTPException(409, "MCP name already exists for this workspace")
    return McpOut(**dict(record))


@mcp_router.get("/{mcp_id}/config", response_model=McpConfigOut)
async def get_mcp_config(
    mcp_id: UUID,
    deps: IntegrationsApp = Depends(get_integrations),
) -> McpConfigOut:
    if not await deps.find_mcp(mcp_id):
        raise HTTPException(404, "MCP not found")
    config = await deps.get_decrypted_mcp(mcp_id)
    return McpConfigOut(config=config)


@mcp_router.patch("/{mcp_id}", response_model=McpOut)
async def update_mcp(
    mcp_id: UUID,
    body: McpUpdate,
    deps: IntegrationsApp = Depends(get_integrations),
) -> McpOut:
    if not await deps.find_mcp(mcp_id):
        raise HTTPException(404, "MCP not found")
    record = await deps.update_mcp(mcp_id, name=body.name, config=body.config)
    return McpOut(**dict(record))


@mcp_router.delete("/{mcp_id}", status_code=204)
async def delete_mcp(
    mcp_id: UUID,
    deps: IntegrationsApp = Depends(get_integrations),
) -> None:
    if not await deps.find_mcp(mcp_id):
        raise HTTPException(404, "MCP not found")
    await deps.delete_mcp(mcp_id)


@templates_router.post("", response_model=TemplateOut, status_code=201)
async def create_template(
    body: TemplateCreate,
    deps: IntegrationsApp = Depends(get_integrations),
) -> TemplateOut:
    record = await deps.create_template(body.workspace_id, body.name, body.template_type, body.content)
    return TemplateOut(**dict(record))


@templates_router.patch("/{template_id}", response_model=TemplateOut)
async def update_template(
    template_id: UUID,
    body: TemplateUpdate,
    deps: IntegrationsApp = Depends(get_integrations),
) -> TemplateOut:
    record = await deps.update_template(template_id, name=body.name, content=body.content)
    if not record:
        raise HTTPException(404, "Template not found")
    return TemplateOut(**dict(record))


@templates_router.delete("/{template_id}", status_code=204)
async def delete_template(
    template_id: UUID,
    deps: IntegrationsApp = Depends(get_integrations),
) -> None:
    if not await deps.find_template(template_id):
        raise HTTPException(404, "Template not found")
    await deps.delete_template(template_id)


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
    try:
        await deps.attach_channel(agent_id, channel_id)
    except asyncpg.UniqueViolationError:
        raise HTTPException(409, "Channel already assigned to another agent")


@links_router.delete("/channels/{channel_id}", status_code=204)
async def detach_channel(
    agent_id: UUID, channel_id: UUID,
    deps: IntegrationsApp = Depends(get_integrations),
) -> None:
    await deps.detach_channel(agent_id, channel_id)


@links_router.post("/mcp/{mcp_id}", status_code=204)
async def attach_mcp(
    agent_id: UUID, mcp_id: UUID,
    deps: IntegrationsApp = Depends(get_integrations),
) -> None:
    await deps.attach_mcp(agent_id, mcp_id)


@links_router.delete("/mcp/{mcp_id}", status_code=204)
async def detach_mcp(
    agent_id: UUID, mcp_id: UUID,
    deps: IntegrationsApp = Depends(get_integrations),
) -> None:
    await deps.detach_mcp(agent_id, mcp_id)


@links_router.post("/templates/{template_id}", status_code=204)
async def attach_template(
    agent_id: UUID, template_id: UUID,
    deps: IntegrationsApp = Depends(get_integrations),
) -> None:
    template = await deps.find_template(template_id)
    if not template:
        raise HTTPException(404, "Template not found")
    await deps.attach_template(agent_id, template_id, template["template_type"])


@links_router.delete("/templates/{template_id}", status_code=204)
async def detach_template(
    agent_id: UUID, template_id: UUID,
    deps: IntegrationsApp = Depends(get_integrations),
) -> None:
    await deps.detach_template(agent_id, template_id)


# ---------- Crons ----------


@crons_router.post("", response_model=CronOut, status_code=201)
async def create_cron(
    body: CronCreate,
    deps: IntegrationsApp = Depends(get_integrations),
) -> CronOut:
    try:
        record = await deps.create_cron(
            body.workspace_id, body.name, body.schedule_kind,
            body.schedule_at_ms, body.schedule_every_ms,
            body.schedule_expr, body.schedule_tz,
            body.message, body.deliver, body.channel, body.recipient,
            body.delete_after_run,
        )
    except asyncpg.UniqueViolationError:
        raise HTTPException(409, "Cron name already exists for this workspace")
    return CronOut(**dict(record))


@crons_router.patch("/{cron_id}", response_model=CronOut)
async def update_cron(
    cron_id: UUID,
    body: CronUpdate,
    deps: IntegrationsApp = Depends(get_integrations),
) -> CronOut:
    if not await deps.find_cron(cron_id):
        raise HTTPException(404, "Cron not found")
    fields = body.model_dump(exclude_none=True)
    record = await deps.update_cron(cron_id, **fields)
    if not record:
        raise HTTPException(404, "Cron not found")
    return CronOut(**dict(record))


@crons_router.delete("/{cron_id}", status_code=204)
async def delete_cron(
    cron_id: UUID,
    deps: IntegrationsApp = Depends(get_integrations),
) -> None:
    if not await deps.find_cron(cron_id):
        raise HTTPException(404, "Cron not found")
    await deps.delete_cron(cron_id)


@links_router.post("/crons/{cron_id}", status_code=204)
async def attach_cron(
    agent_id: UUID, cron_id: UUID,
    deps: IntegrationsApp = Depends(get_integrations),
) -> None:
    if not await deps.find_cron(cron_id):
        raise HTTPException(404, "Cron not found")
    await deps.attach_cron(agent_id, cron_id)


@links_router.delete("/crons/{cron_id}", status_code=204)
async def detach_cron(
    agent_id: UUID, cron_id: UUID,
    deps: IntegrationsApp = Depends(get_integrations),
) -> None:
    await deps.detach_cron(agent_id, cron_id)


@links_router.patch("/crons/{cron_id}", response_model=AgentCronWithCronOut)
async def update_agent_cron(
    agent_id: UUID, cron_id: UUID,
    body: AgentCronUpdate,
    deps: IntegrationsApp = Depends(get_integrations),
) -> AgentCronWithCronOut:
    if body.enabled is None:
        raise HTTPException(400, "No fields to update")
    updated = await deps.set_agent_cron_enabled(agent_id, cron_id, body.enabled)
    if not updated:
        raise HTTPException(404, "Agent-cron attachment not found")
    # Re-read joined view for response payload.
    rows = await deps.list_agent_crons(agent_id)
    for row in rows:
        if row["id"] == cron_id:
            return AgentCronWithCronOut(**row)
    raise HTTPException(404, "Agent-cron attachment vanished")
