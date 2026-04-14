import logging
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, UploadFile, File

from src.knowledge.app import KnowledgeApp
from src.knowledge.core.schema import GraphData, IngestTextRequest, QueryRequest, QueryResponse

router = APIRouter()
logger = logging.getLogger(__name__)


def get_knowledge(request: Request) -> KnowledgeApp:
    return request.app.state.knowledge


async def get_knowledge_workspace_id(request: Request) -> UUID:
    """Extract workspace_id from bearer token."""
    from src.workspace.app import WorkspaceApp
    workspace: WorkspaceApp = request.app.state.workspace
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        raise HTTPException(401, "Missing Authorization header")
    token = auth[7:]
    record = await workspace.find_by_token(token)
    if not record:
        raise HTTPException(401, "Invalid token")
    return record["id"]


async def _ingest_with_logging(
    knowledge: KnowledgeApp, workspace_id: UUID, text: str, metadata: dict
) -> None:
    try:
        await knowledge.ingest(workspace_id, text, metadata)
    except Exception:
        logger.exception("Background ingest failed for workspace %s", workspace_id)


async def _ingest_file_with_logging(
    knowledge: KnowledgeApp, workspace_id: UUID, content: bytes, content_type: str, filename: str
) -> None:
    try:
        await knowledge.ingest_file(workspace_id, content, content_type, filename)
    except Exception:
        logger.exception("Background file ingest failed for workspace %s file %s", workspace_id, filename)


@router.post("/ingest/text", status_code=202)
async def ingest_text(
    body: IngestTextRequest,
    background_tasks: BackgroundTasks,
    knowledge: KnowledgeApp = Depends(get_knowledge),
    workspace_id: UUID = Depends(get_knowledge_workspace_id),
) -> dict:
    """Ingest raw text into the knowledge graph. Indexing runs in the background."""
    background_tasks.add_task(_ingest_with_logging, knowledge, workspace_id, body.text, body.metadata)
    return {"status": "queued"}


@router.post("/ingest/file", status_code=202)
async def ingest_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    knowledge: KnowledgeApp = Depends(get_knowledge),
    workspace_id: UUID = Depends(get_knowledge_workspace_id),
) -> dict:
    """Upload a file for background ingestion. Docling normalises to Markdown before indexing."""
    allowed = {
        "text/plain",
        "text/markdown",
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "text/html",
        "image/png",
        "image/jpeg",
        "image/webp",
    }
    if file.content_type not in allowed:
        raise HTTPException(415, f"Unsupported file type: {file.content_type}")
    content = await file.read()
    background_tasks.add_task(
        _ingest_file_with_logging,
        knowledge,
        workspace_id,
        content,
        file.content_type,
        file.filename or "unknown",
    )
    return {"status": "queued", "filename": file.filename}


@router.post("/query", response_model=QueryResponse)
async def query_knowledge(
    body: QueryRequest,
    knowledge: KnowledgeApp = Depends(get_knowledge),
    workspace_id: UUID = Depends(get_knowledge_workspace_id),
) -> QueryResponse:
    """Query the knowledge graph."""
    answer = await knowledge.query(workspace_id, body.query, body.mode)
    return QueryResponse(answer=answer)


@router.get("/graph", response_model=GraphData)
async def get_graph(
    knowledge: KnowledgeApp = Depends(get_knowledge),
    workspace_id: UUID = Depends(get_knowledge_workspace_id),
) -> GraphData:
    """Return graph nodes and edges for visualisation."""
    data = await knowledge.get_graph(workspace_id)
    return GraphData(
        nodes=data.get("nodes", []),
        edges=data.get("edges", []),
    )
