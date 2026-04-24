from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request

from src.workspace.app import WorkspaceApp
from src.workspace.core.schema import WorkspaceCreate, WorkspaceOut, WorkspaceUpdate

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


@router.patch("/{workspace_id}", response_model=WorkspaceOut)
async def update_workspace(
    workspace_id: UUID,
    body: WorkspaceUpdate,
    workspace: WorkspaceApp = Depends(get_workspace),
) -> WorkspaceOut:
    if body.name is None and body.slug is None:
        raise HTTPException(status_code=400, detail="At least one field required")
    try:
        record = await workspace.update_workspace(workspace_id, body.name, body.slug)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if record is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return WorkspaceOut(**dict(record))


@router.delete("/{workspace_id}", status_code=204)
async def delete_workspace(
    workspace_id: UUID,
    workspace: WorkspaceApp = Depends(get_workspace),
) -> None:
    await workspace.delete_workspace(workspace_id)
