from uuid import UUID

from pydantic import BaseModel


class GraphNode(BaseModel):
    id: UUID
    name: str
    type: str
    mastery: int
    importance: int
    knowledge_gap: bool = False


class GraphEdge(BaseModel):
    id: UUID
    source: UUID
    target: UUID
    type: str


class GraphRead(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    truncated: bool = False


class ConceptSummary(BaseModel):
    id: UUID
    name: str
    type: str


class ConceptSourceSummary(BaseModel):
    id: UUID
    title: str
    type: str


class ConceptDetail(BaseModel):
    id: UUID
    name: str
    type: str
    description: str
    importance: int
    confidence: int
    mastery: int
    knowledge_status: str
    aliases: list[str]
    prerequisites: list[ConceptSummary]
    unlocks: list[ConceptSummary]
    sources: list[ConceptSourceSummary]
