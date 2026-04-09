from collections.abc import AsyncGenerator
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from src.fleet.app import FleetApp
from src.fleet.core.schema import AgentCreate, AgentFileIn, AgentFileOut, AgentOut, AgentUpdate

router = APIRouter()


def get_fleet(request: Request) -> FleetApp:
    return request.app.state.fleet


@router.post("", response_model=AgentOut, status_code=201)
async def create_agent(
    body: AgentCreate,
    fleet: FleetApp = Depends(get_fleet),
) -> AgentOut:
    record = await fleet.create_agent(body.user_id, body.name, body.image, body.is_admin)
    return AgentOut(**dict(record))


@router.get("", response_model=list[AgentOut])
async def list_agents(
    user_id: UUID,
    fleet: FleetApp = Depends(get_fleet),
) -> list[AgentOut]:
    records = await fleet.list_agents(user_id)
    return [AgentOut(**dict(r)) for r in records]


@router.get("/{agent_id}", response_model=AgentOut)
async def get_agent(
    agent_id: UUID,
    fleet: FleetApp = Depends(get_fleet),
) -> AgentOut:
    record = await fleet.find_agent(agent_id)
    if not record:
        raise HTTPException(404, "Agent not found")
    return AgentOut(**dict(record))


@router.patch("/{agent_id}", response_model=AgentOut)
async def update_agent(
    agent_id: UUID,
    body: AgentUpdate,
    fleet: FleetApp = Depends(get_fleet),
) -> AgentOut:
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(400, "No fields to update")
    record = await fleet.update_agent(agent_id, **updates)
    if not record:
        raise HTTPException(404, "Agent not found")
    return AgentOut(**dict(record))


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(
    agent_id: UUID,
    fleet: FleetApp = Depends(get_fleet),
) -> None:
    record = await fleet.find_agent(agent_id)
    if not record:
        raise HTTPException(404, "Agent not found")
    await fleet.delete_agent(agent_id)


@router.post("/{agent_id}/start", response_model=AgentOut)
async def start_agent(
    agent_id: UUID,
    fleet: FleetApp = Depends(get_fleet),
) -> AgentOut:
    record = await fleet.find_agent(agent_id)
    if not record:
        raise HTTPException(404, "Agent not found")
    if record["status"] == "running":
        raise HTTPException(409, "Agent is already running")
    await fleet.start_sandbox(agent_id)
    updated = await fleet.find_agent(agent_id)
    return AgentOut(**dict(updated))


@router.post("/{agent_id}/stop", response_model=AgentOut)
async def stop_agent(
    agent_id: UUID,
    fleet: FleetApp = Depends(get_fleet),
) -> AgentOut:
    record = await fleet.find_agent(agent_id)
    if not record:
        raise HTTPException(404, "Agent not found")
    if record["status"] != "running":
        raise HTTPException(409, "Agent is not running")
    await fleet.stop_sandbox(agent_id)
    updated = await fleet.find_agent(agent_id)
    return AgentOut(**dict(updated))


@router.post("/{agent_id}/chat")
async def chat_agent(
    agent_id: UUID,
    request: Request,
    fleet: FleetApp = Depends(get_fleet),
) -> StreamingResponse:
    record = await fleet.find_agent(agent_id)
    if not record:
        raise HTTPException(404, "Agent not found")
    if record["status"] != "running":
        raise HTTPException(409, "Agent is not running")
    if not record["gateway_port"]:
        raise HTTPException(503, "Agent gateway not available")

    body = await request.body()
    headers = {
        k: v for k, v in request.headers.items()
        if k.lower() in ("content-type", "accept")
    }
    gateway_url = f"http://localhost:{record['gateway_port']}/chat"

    async def stream() -> AsyncGenerator[bytes, None]:
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("POST", gateway_url, content=body, headers=headers) as resp:
                async for chunk in resp.aiter_bytes():
                    yield chunk

    return StreamingResponse(stream(), media_type="text/event-stream")


@router.put("/{agent_id}/files", response_model=AgentFileOut)
async def upsert_file(
    agent_id: UUID,
    body: AgentFileIn,
    fleet: FleetApp = Depends(get_fleet),
) -> AgentFileOut:
    record = await fleet.upsert_file(agent_id, body.path, body.content)
    return AgentFileOut(**dict(record))


@router.get("/{agent_id}/files", response_model=list[AgentFileOut])
async def list_files(
    agent_id: UUID,
    fleet: FleetApp = Depends(get_fleet),
) -> list[AgentFileOut]:
    records = await fleet.list_files(agent_id)
    return [AgentFileOut(**dict(r)) for r in records]


@router.get("/{agent_id}/files/{path:path}", response_model=AgentFileOut)
async def get_file(
    agent_id: UUID,
    path: str,
    fleet: FleetApp = Depends(get_fleet),
) -> AgentFileOut:
    record = await fleet.find_file(agent_id, path)
    if not record:
        raise HTTPException(404, "File not found")
    return AgentFileOut(**dict(record))
