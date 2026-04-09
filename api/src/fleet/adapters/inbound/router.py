from collections.abc import AsyncGenerator
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
import asyncpg
import httpx
from src.shared.db.pool import get_pool
from src.fleet.core.schema import AgentCreate, AgentOut, AgentUpdate
from src.fleet.adapters.outbound.repository import AgentRepo
from src.fleet.core.schema import AgentFileIn, AgentFileOut
from src.fleet.adapters.outbound.repository import AgentFileRepo

router = APIRouter()


def get_repo(pool: asyncpg.Connection = Depends(get_pool)) -> AgentRepo:
    return AgentRepo(pool)


@router.post("", response_model=AgentOut, status_code=201)
async def create_agent(
    body: AgentCreate, repo: AgentRepo = Depends(get_repo)
) -> AgentOut:
    record = await repo.create(body.user_id, body.name, body.image, body.is_admin)
    return AgentOut(**dict(record))


@router.get("", response_model=list[AgentOut])
async def list_agents(
    user_id: UUID, repo: AgentRepo = Depends(get_repo)
) -> list[AgentOut]:
    records = await repo.list_by_user(user_id)
    return [AgentOut(**dict(r)) for r in records]


@router.get("/{agent_id}", response_model=AgentOut)
async def get_agent(agent_id: UUID, repo: AgentRepo = Depends(get_repo)) -> AgentOut:
    record = await repo.find_by_id(agent_id)
    if not record:
        raise HTTPException(404, "Agent not found")
    return AgentOut(**dict(record))


@router.patch("/{agent_id}", response_model=AgentOut)
async def update_agent(
    agent_id: UUID, body: AgentUpdate, repo: AgentRepo = Depends(get_repo)
) -> AgentOut:
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(400, "No fields to update")
    record = await repo.update(agent_id, **updates)
    if not record:
        raise HTTPException(404, "Agent not found")
    return AgentOut(**dict(record))


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(agent_id: UUID, repo: AgentRepo = Depends(get_repo)) -> None:
    record = await repo.find_by_id(agent_id)
    if not record:
        raise HTTPException(404, "Agent not found")
    await repo.delete(agent_id)


@router.post("/{agent_id}/start", response_model=AgentOut)
async def start_agent(
    agent_id: UUID,
    conn: asyncpg.Connection = Depends(get_pool),
) -> AgentOut:
    record = await AgentRepo(conn).find_by_id(agent_id)
    if not record:
        raise HTTPException(404, "Agent not found")
    if record["status"] == "running":
        raise HTTPException(409, "Agent is already running")
    from src.fleet.app.sandbox import start_agent_sandbox

    await start_agent_sandbox(conn, agent_id)
    updated = await AgentRepo(conn).find_by_id(agent_id)
    return AgentOut(**dict(updated))


@router.post("/{agent_id}/stop", response_model=AgentOut)
async def stop_agent(
    agent_id: UUID,
    conn: asyncpg.Connection = Depends(get_pool),
) -> AgentOut:
    record = await AgentRepo(conn).find_by_id(agent_id)
    if not record:
        raise HTTPException(404, "Agent not found")
    if record["status"] != "running":
        raise HTTPException(409, "Agent is not running")
    from src.fleet.app.sandbox import stop_agent_sandbox

    await stop_agent_sandbox(conn, agent_id)
    updated = await AgentRepo(conn).find_by_id(agent_id)
    return AgentOut(**dict(updated))


@router.post("/{agent_id}/chat")
async def chat_agent(
    agent_id: UUID,
    request: Request,
    conn: asyncpg.Connection = Depends(get_pool),
) -> StreamingResponse:
    record = await AgentRepo(conn).find_by_id(agent_id)
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


def get_file_repo(pool: asyncpg.Connection = Depends(get_pool)) -> AgentFileRepo:
    return AgentFileRepo(pool)


@router.put("/{agent_id}/files", response_model=AgentFileOut)
async def upsert_file(
    agent_id: UUID,
    body: AgentFileIn,
    repo: AgentFileRepo = Depends(get_file_repo),
) -> AgentFileOut:
    record = await repo.upsert(agent_id, body.path, body.content)
    return AgentFileOut(**dict(record))


@router.get("/{agent_id}/files", response_model=list[AgentFileOut])
async def list_files(
    agent_id: UUID, repo: AgentFileRepo = Depends(get_file_repo)
) -> list[AgentFileOut]:
    records = await repo.list_by_agent(agent_id)
    return [AgentFileOut(**dict(r)) for r in records]


@router.get("/{agent_id}/files/{path:path}", response_model=AgentFileOut)
async def get_file(
    agent_id: UUID, path: str, repo: AgentFileRepo = Depends(get_file_repo)
) -> AgentFileOut:
    record = await repo.find(agent_id, path)
    if not record:
        raise HTTPException(404, "File not found")
    return AgentFileOut(**dict(record))
