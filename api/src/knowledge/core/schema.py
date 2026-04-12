from pydantic import BaseModel


class IngestTextRequest(BaseModel):
    text: str
    metadata: dict = {}


class QueryRequest(BaseModel):
    query: str
    mode: str = "hybrid"  # local | global | hybrid | naive


class QueryResponse(BaseModel):
    answer: str


class GraphNode(BaseModel):
    id: str
    type: str = ""
    description: str = ""


class GraphEdge(BaseModel):
    source: str
    target: str
    label: str = ""
    weight: float = 1.0


class GraphData(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
