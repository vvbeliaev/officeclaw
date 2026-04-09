from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
import asyncpg
from src.db.pool import get_pool
from src.models.channel import ChannelCreate, ChannelOut
from src.repositories.channels import ChannelRepo

router = APIRouter()


def get_repo(pool: asyncpg.Connection = Depends(get_pool)) -> ChannelRepo:
    return ChannelRepo(pool)


@router.post("", response_model=ChannelOut, status_code=201)
async def create_channel(body: ChannelCreate, repo: ChannelRepo = Depends(get_repo)) -> ChannelOut:
    record = await repo.create(body.user_id, body.type, body.config)
    return ChannelOut(**dict(record))


@router.get("", response_model=list[ChannelOut])
async def list_channels(user_id: UUID, repo: ChannelRepo = Depends(get_repo)) -> list[ChannelOut]:
    return [ChannelOut(**dict(r)) for r in await repo.list_by_user(user_id)]


@router.delete("/{channel_id}", status_code=204)
async def delete_channel(channel_id: UUID, repo: ChannelRepo = Depends(get_repo)) -> None:
    if not await repo.find_by_id(channel_id):
        raise HTTPException(404, "Channel not found")
    await repo.delete(channel_id)
