# api/src/routers/agents.py
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
import asyncpg
from src.db.pool import get_pool
from src.models.agent import AgentCreate, AgentOut, AgentUpdate
from src.repositories.agents import AgentRepo

router = APIRouter()


def get_repo(pool: asyncpg.Connection = Depends(get_pool)) -> AgentRepo:
    return AgentRepo(pool)


@router.post("", response_model=AgentOut, status_code=201)
async def create_agent(body: AgentCreate, repo: AgentRepo = Depends(get_repo)) -> AgentOut:
    record = await repo.create(body.user_id, body.name, body.image, body.is_admin)
    return AgentOut(**dict(record))


@router.get("", response_model=list[AgentOut])
async def list_agents(user_id: UUID, repo: AgentRepo = Depends(get_repo)) -> list[AgentOut]:
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
