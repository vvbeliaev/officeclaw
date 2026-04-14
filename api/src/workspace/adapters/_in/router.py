from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request

from src.workspace.app import WorkspaceApp
from src.workspace.core.schema import WorkspaceCreate, WorkspaceOut

router = APIRouter()


def get_workspace(request: Request) -> WorkspaceApp:
    return request.app.state.workspace


@router.post("", response_model=WorkspaceOut, status_code=201)
async def create_workspace(
    body: WorkspaceCreate,
    workspace: WorkspaceApp = Depends(get_workspace),
) -> WorkspaceOut:
    record = await workspace.create_workspace(body.user_id, body.name)
    return WorkspaceOut(**dict(record))


@router.get("", response_model=list[WorkspaceOut])
async def list_workspaces(
    user_id: UUID,
    workspace: WorkspaceApp = Depends(get_workspace),
) -> list[WorkspaceOut]:
    records = await workspace.list_workspaces(user_id)
    return [WorkspaceOut(**dict(r)) for r in records]
