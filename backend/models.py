from pydantic import BaseModel


class QueryRequest(BaseModel):
    question: str
    top_k: int = 5


class GraphNode(BaseModel):
    id: str
    label: str
    properties: dict


class GraphEdge(BaseModel):
    source: str
    target: str
    relationship: str


class GraphContext(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class Citation(BaseModel):
    entity_name: str
    entity_type: str
    relevance: str


class QueryResponse(BaseModel):
    answer: str
    citations: list[Citation]
    graph_context: GraphContext
    retrieval_method: str
    latency_ms: int
