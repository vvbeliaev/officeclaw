from typing import Literal
from pydantic import BaseModel

QueryMode = Literal["local", "global", "hybrid", "naive", "mix", "bypass"]


class IngestTextRequest(BaseModel):
    text: str
    metadata: dict = {}


class QueryRequest(BaseModel):
    query: str
    mode: QueryMode = "hybrid"


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
