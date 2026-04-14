import json
import shutil
from collections.abc import AsyncGenerator
from pathlib import Path
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse

from src.fleet.app import FleetApp
from src.fleet.app.sandbox import gateway_base_url
from src.fleet.core.schema import (
    AgentCreate,
    AgentFileIn,
    AgentFileOut,
    AgentOut,
    AgentUpdate,
)

router = APIRouter()


def get_fleet(request: Request) -> FleetApp:
    return request.app.state.fleet


@router.post("", response_model=AgentOut, status_code=201)
async def create_agent(
    body: AgentCreate,
    fleet: FleetApp = Depends(get_fleet),
) -> AgentOut:
    record = await fleet.create_agent(
        body.workspace_id, body.name, body.image, body.is_admin
    )
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


@router.post("/{agent_id}/v1/chat/completions")
async def proxy_chat_completions(
    agent_id: UUID,
    request: Request,
    fleet: FleetApp = Depends(get_fleet),
) -> StreamingResponse:
    """Transparent proxy to the nanobot gateway's /v1/chat/completions.

    Supports both stream=false (JSON) and stream=true (SSE).
    The BFF uses @ai-sdk/openai pointing at this endpoint, so no format
    translation is needed here — bytes flow through unchanged.
    """
    record = await fleet.find_agent(agent_id)
    if not record:
        raise HTTPException(404, "Agent not found")
    if record["status"] != "running":
        raise HTTPException(409, "Agent is not running")
    if not record["gateway_port"]:
        raise HTTPException(503, "Agent gateway not available")

    body = await request.body()
    gateway_url = f"{gateway_base_url(record['gateway_port'])}/v1/chat/completions"

    async def stream() -> AsyncGenerator[bytes, None]:
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST",
                gateway_url,
                content=body,
                headers={"Content-Type": "application/json"},
            ) as resp:
                if resp.status_code >= 400:
                    error_body = await resp.aread()
                    raise HTTPException(resp.status_code, error_body.decode())
                async for chunk in resp.aiter_bytes():
                    yield chunk

    # Detect streaming from the JSON body's "stream" flag.
    # @ai-sdk/openai does not send Accept: text/event-stream — it uses stream:true.
    try:
        is_streaming = json.loads(body).get("stream", False)
    except (json.JSONDecodeError, AttributeError):
        is_streaming = False
    media_type = "text/event-stream" if is_streaming else "application/json"

    return StreamingResponse(stream(), media_type=media_type)


_AVATAR_DIR = Path("uploads/avatars")
_ALLOWED_AVATAR_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


@router.post("/{agent_id}/avatar", response_model=AgentOut)
async def upload_avatar(
    agent_id: UUID,
    request: Request,
    file: UploadFile = File(...),
    fleet: FleetApp = Depends(get_fleet),
) -> AgentOut:
    record = await fleet.find_agent(agent_id)
    if not record:
        raise HTTPException(404, "Agent not found")
    if file.content_type not in _ALLOWED_AVATAR_TYPES:
        raise HTTPException(415, "Unsupported image type")

    _AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename or "avatar.jpg").suffix.lower() or ".jpg"
    filename = f"{agent_id}{ext}"
    dest = _AVATAR_DIR / filename

    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    base = str(request.base_url).rstrip("/")
    avatar_url = f"{base}/static/avatars/{filename}"
    updated = await fleet.update_agent(agent_id, avatar_url=avatar_url)
    return AgentOut(**dict(updated))


@router.put("/{agent_id}/files", response_model=AgentFileOut)
async def upsert_file(
    agent_id: UUID,
    body: AgentFileIn,
    fleet: FleetApp = Depends(get_fleet),
) -> AgentFileOut:
    agent = await fleet.find_agent(agent_id)
    if not agent:
        raise HTTPException(404, "Agent not found")
    if agent["status"] == "running":
        raise HTTPException(409, "Cannot edit files while agent is running — stop the agent first")
    record = await fleet.upsert_file(agent_id, body.path, body.content)
    return AgentFileOut(**dict(record))
