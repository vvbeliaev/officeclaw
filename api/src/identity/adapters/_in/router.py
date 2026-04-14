from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Request

from src.identity.app import IdentityApp
from src.identity.core.schema import BootstrapOut, UserCreate, UserRegistered

router = APIRouter()


def get_identity(request: Request) -> IdentityApp:
    return request.app.state.identity


@router.post("", response_model=UserRegistered, status_code=201)
async def create_user(
    body: UserCreate,
    identity: IdentityApp = Depends(get_identity),
) -> UserRegistered:
    try:
        user, workspace = await identity.register(body.email)
    except asyncpg.UniqueViolationError:
        raise HTTPException(409, "Email already registered")
    return UserRegistered(
        id=user["id"],
        email=user["email"],
        workspace_id=workspace["id"],
        officeclaw_token=workspace["officeclaw_token"],
        created_at=user["created_at"],
    )


@router.post("/{user_id}/bootstrap", response_model=BootstrapOut, status_code=201)
async def bootstrap_user(
    user_id: UUID,
    identity: IdentityApp = Depends(get_identity),
) -> BootstrapOut:
    """Called by SvelteKit after better-auth creates a new user."""
    try:
        workspace = await identity.bootstrap(user_id)
    except asyncpg.UniqueViolationError:
        raise HTTPException(409, "User already bootstrapped")
    except ValueError as e:
        raise HTTPException(404, str(e))
    return BootstrapOut(
        workspace_id=workspace["id"],
        officeclaw_token=workspace["officeclaw_token"],
    )
