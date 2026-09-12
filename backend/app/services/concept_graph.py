from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.concept import Concept, ConceptEdge

RELATION_TYPES = {
    "prerequisite_of",
    "part_of",
    "related_to",
    "used_for",
    "example_of",
    "depends_on",
    "contrasts_with",
}


class ConceptGraphService:
    def __init__(self, db: Session, workspace_id: UUID) -> None:
        self.db = db
        self.workspace_id = workspace_id

    def add_edge(
        self,
        source_id: UUID,
        target_id: UUID,
        relation_type: str,
        confidence: float,
    ) -> ConceptEdge:
        if relation_type not in RELATION_TYPES:
            raise AppError(422, "INVALID_RELATION_TYPE", "The relationship type is not allowed.")
        if not 0 <= confidence <= 1:
            raise AppError(422, "INVALID_CONFIDENCE", "Relationship confidence must be 0 to 1.")
        if source_id == target_id:
            raise AppError(422, "SELF_RELATION", "A concept cannot relate to itself.")
        self._require_concepts(source_id, target_id)

        existing = self.db.scalar(
            select(ConceptEdge).where(
                ConceptEdge.workspace_id == self.workspace_id,
                ConceptEdge.source_concept_id == source_id,
                ConceptEdge.target_concept_id == target_id,
                ConceptEdge.relation_type == relation_type,
            )
        )
        if existing:
            existing.confidence = max(existing.confidence, confidence)
            return existing
        if relation_type == "prerequisite_of" and self._has_prerequisite_path(target_id, source_id):
            raise AppError(409, "PREREQUISITE_CYCLE", "This relationship would create a cycle.")

        edge = ConceptEdge(
            workspace_id=self.workspace_id,
            source_concept_id=source_id,
            target_concept_id=target_id,
            relation_type=relation_type,
            confidence=confidence,
        )
        self.db.add(edge)
        self.db.flush()
        return edge

    def _require_concepts(self, *concept_ids: UUID) -> None:
        found = set(
            self.db.scalars(
                select(Concept.id).where(
                    Concept.workspace_id == self.workspace_id,
                    Concept.id.in_(concept_ids),
                )
            )
        )
        if found != set(concept_ids):
            raise AppError(404, "CONCEPT_NOT_FOUND", "A relationship concept was not found.")

    def _has_prerequisite_path(self, start_id: UUID, target_id: UUID) -> bool:
        edges = self.db.execute(
            select(ConceptEdge.source_concept_id, ConceptEdge.target_concept_id).where(
                ConceptEdge.workspace_id == self.workspace_id,
                ConceptEdge.relation_type == "prerequisite_of",
            )
        )
        adjacency: dict[UUID, set[UUID]] = {}
        for source_id, destination_id in edges:
            adjacency.setdefault(source_id, set()).add(destination_id)
        pending = [start_id]
        visited: set[UUID] = set()
        while pending:
            current = pending.pop()
            if current == target_id:
                return True
            if current in visited:
                continue
            visited.add(current)
            pending.extend(adjacency.get(current, ()))
        return False
