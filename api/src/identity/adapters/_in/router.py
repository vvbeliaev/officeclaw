from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request

from src.identity.app import IdentityApp
from src.identity.core.schema import BootstrapOut

router = APIRouter()


def get_identity(request: Request) -> IdentityApp:
    return request.app.state.identity


@router.post("/{user_id}/bootstrap", response_model=BootstrapOut, status_code=201)
async def bootstrap_user(
    user_id: UUID,
    identity: IdentityApp = Depends(get_identity),
) -> BootstrapOut:
    """Called by SvelteKit after better-auth creates a new user. Idempotent:
    re-invoking for an already-bootstrapped user returns the existing workspace."""
    try:
        workspace = await identity.bootstrap(user_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return BootstrapOut(
        workspace_id=workspace["id"],
        officeclaw_token=workspace["officeclaw_token"],
    )
