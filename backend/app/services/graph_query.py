from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError
from app.models.ai import AISetting
from app.models.concept import Concept, ConceptAlias, ConceptEdge, ConceptSource
from app.models.learning import KnowledgeState
from app.models.source import Source
from app.models.workspace import Workspace
from app.schemas.graph import (
    ConceptDetail,
    ConceptSourceSummary,
    ConceptSummary,
    GraphEdge,
    GraphNode,
    GraphRead,
)
from app.services.ai.factory import create_provider
from app.services.concept_matcher import cosine_similarity, normalize_concept_name
from app.services.learning import knowledge_status

GRAPH_NODE_LIMIT = 200
OVERVIEW_NODE_LIMIT = 50


class GraphQueryService:
    def __init__(self, db: Session, user_id: UUID) -> None:
        self.db = db
        self.user_id = user_id

    def graph(
        self,
        workspace_id: UUID,
        focus_id: UUID | None = None,
        depth: int = 2,
        overview: bool = False,
        source_id: UUID | None = None,
    ) -> GraphRead:
        self._require_workspace(workspace_id)
        source_concepts = None
        if source_id:
            source = self.db.get(Source, source_id)
            if not source or source.workspace_id != workspace_id:
                raise AppError(404, "SOURCE_NOT_FOUND", "Source was not found.")
            source_concepts = select(ConceptSource.concept_id).where(
                ConceptSource.source_id == source_id
            )
        if focus_id and not overview:
            concept_ids, truncated = self._neighbor_ids(workspace_id, focus_id, depth)
            if source_concepts is not None:
                concept_ids &= set(self.db.scalars(source_concepts))
            concepts = list(self.db.scalars(select(Concept).where(Concept.id.in_(concept_ids))))
        else:
            concepts = list(
                self.db.scalars(
                    select(Concept)
                    .where(Concept.workspace_id == workspace_id)
                    .where(Concept.id.in_(source_concepts) if source_concepts is not None else True)
                    .order_by(Concept.importance.desc(), Concept.name)
                    .limit((GRAPH_NODE_LIMIT if source_id else OVERVIEW_NODE_LIMIT) + 1)
                )
            )
            limit = GRAPH_NODE_LIMIT if source_id else OVERVIEW_NODE_LIMIT
            truncated = len(concepts) > limit
            concepts = concepts[:limit]

        ids = {concept.id for concept in concepts}
        states = self._knowledge_states(ids)
        edges = (
            list(
                self.db.scalars(
                    select(ConceptEdge).where(
                        ConceptEdge.workspace_id == workspace_id,
                        ConceptEdge.source_concept_id.in_(ids),
                        ConceptEdge.target_concept_id.in_(ids),
                    )
                )
            )
            if ids
            else []
        )
        gap_ids = self._gap_ids(edges, states)
        return GraphRead(
            nodes=[
                self._node(concept, states.get(concept.id), concept.id in gap_ids)
                for concept in concepts
            ],
            edges=[
                GraphEdge(
                    id=edge.id,
                    source=edge.source_concept_id,
                    target=edge.target_concept_id,
                    type=edge.relation_type,
                )
                for edge in edges
            ],
            truncated=truncated,
        )

    def concept_detail(self, concept_id: UUID) -> ConceptDetail:
        concept = self.db.scalar(
            select(Concept)
            .join(Workspace)
            .options(selectinload(Concept.aliases))
            .where(Concept.id == concept_id, Workspace.user_id == self.user_id)
        )
        if not concept:
            raise AppError(404, "CONCEPT_NOT_FOUND", "Concept was not found.")

        prerequisite_edges = list(
            self.db.scalars(
                select(ConceptEdge).where(
                    ConceptEdge.workspace_id == concept.workspace_id,
                    ConceptEdge.target_concept_id == concept.id,
                    ConceptEdge.relation_type == "prerequisite_of",
                )
            )
        )
        unlock_edges = list(
            self.db.scalars(
                select(ConceptEdge).where(
                    ConceptEdge.workspace_id == concept.workspace_id,
                    ConceptEdge.source_concept_id == concept.id,
                    ConceptEdge.relation_type == "prerequisite_of",
                )
            )
        )
        prerequisites = self._concept_summaries(
            [edge.source_concept_id for edge in prerequisite_edges]
        )
        unlocks = self._concept_summaries([edge.target_concept_id for edge in unlock_edges])
        sources = list(
            self.db.scalars(
                select(Source)
                .join(ConceptSource)
                .where(ConceptSource.concept_id == concept.id)
                .distinct()
            )
        )
        state = self.db.scalar(
            select(KnowledgeState).where(
                KnowledgeState.user_id == self.user_id,
                KnowledgeState.concept_id == concept.id,
            )
        )
        mastery = round(state.mastery) if state else 0
        return ConceptDetail(
            id=concept.id,
            name=concept.name,
            type=concept.type,
            description=concept.description,
            importance=round(concept.importance * 100),
            confidence=round(concept.confidence * 100),
            mastery=mastery,
            knowledge_status=knowledge_status(mastery),
            aliases=[alias.alias for alias in concept.aliases],
            prerequisites=prerequisites,
            unlocks=unlocks,
            sources=[
                ConceptSourceSummary(id=item.id, title=item.title, type=item.type)
                for item in sources
            ],
        )

    def search(self, workspace_id: UUID, query: str, limit: int = 10) -> list[GraphNode]:
        self._require_workspace(workspace_id)
        normalized = normalize_concept_name(query)
        if not normalized:
            return []
        direct = list(
            self.db.scalars(
                select(Concept)
                .outerjoin(ConceptAlias)
                .where(
                    Concept.workspace_id == workspace_id,
                    or_(
                        Concept.normalized_name.startswith(normalized),
                        ConceptAlias.normalized_alias.startswith(normalized),
                    ),
                )
                .distinct()
                .order_by(Concept.importance.desc())
                .limit(limit)
            )
        )
        if direct:
            states = self._knowledge_states({concept.id for concept in direct})
            return [self._node(concept, states.get(concept.id)) for concept in direct]
        return self._semantic_search(workspace_id, query, limit)

    def _semantic_search(self, workspace_id: UUID, query: str, limit: int) -> list[GraphNode]:
        setting = self.db.scalar(select(AISetting).where(AISetting.user_id == self.user_id))
        if not setting:
            return []
        try:
            embedding = create_provider(setting).embed(query)
        except Exception:
            return []
        concepts = list(
            self.db.scalars(
                select(Concept).where(
                    Concept.workspace_id == workspace_id,
                    Concept.embedding.is_not(None),
                )
            )
        )
        concepts.sort(
            key=lambda concept: cosine_similarity(embedding, concept.embedding or []), reverse=True
        )
        selected = concepts[:limit]
        states = self._knowledge_states({concept.id for concept in selected})
        return [self._node(concept, states.get(concept.id)) for concept in selected]

    def _neighbor_ids(
        self, workspace_id: UUID, focus_id: UUID, depth: int
    ) -> tuple[set[UUID], bool]:
        focus = self.db.scalar(
            select(Concept.id).where(
                Concept.id == focus_id,
                Concept.workspace_id == workspace_id,
            )
        )
        if not focus:
            raise AppError(404, "CONCEPT_NOT_FOUND", "Concept was not found.")
        selected = {focus_id}
        frontier = {focus_id}
        truncated = False
        for _ in range(max(1, min(depth, 3))):
            rows = self.db.execute(
                select(ConceptEdge.source_concept_id, ConceptEdge.target_concept_id).where(
                    ConceptEdge.workspace_id == workspace_id,
                    or_(
                        ConceptEdge.source_concept_id.in_(frontier),
                        ConceptEdge.target_concept_id.in_(frontier),
                    ),
                )
            )
            neighbors = {concept_id for row in rows for concept_id in row} - selected
            available = GRAPH_NODE_LIMIT - len(selected)
            if len(neighbors) > available:
                neighbors = set(sorted(neighbors, key=str)[:available])
                truncated = True
            selected.update(neighbors)
            frontier = neighbors
            if not frontier or len(selected) >= GRAPH_NODE_LIMIT:
                break
        return selected, truncated

    def _concept_summaries(self, concept_ids: list[UUID]) -> list[ConceptSummary]:
        if not concept_ids:
            return []
        concepts = self.db.scalars(select(Concept).where(Concept.id.in_(concept_ids)))
        return [ConceptSummary(id=item.id, name=item.name, type=item.type) for item in concepts]

    def _node(
        self,
        concept: Concept,
        state: KnowledgeState | None = None,
        knowledge_gap: bool = False,
    ) -> GraphNode:
        return GraphNode(
            id=concept.id,
            name=concept.name,
            type=concept.type,
            mastery=round(state.mastery) if state else 0,
            importance=round(concept.importance * 100),
            knowledge_gap=knowledge_gap,
        )

    def _knowledge_states(self, concept_ids: set[UUID]) -> dict[UUID, KnowledgeState]:
        if not concept_ids:
            return {}
        states = self.db.scalars(
            select(KnowledgeState).where(
                KnowledgeState.user_id == self.user_id,
                KnowledgeState.concept_id.in_(concept_ids),
            )
        )
        return {state.concept_id: state for state in states}

    def _gap_ids(self, edges: list[ConceptEdge], states: dict[UUID, KnowledgeState]) -> set[UUID]:
        gaps: set[UUID] = set()
        for edge in edges:
            if edge.relation_type != "prerequisite_of":
                continue
            prerequisite = states.get(edge.source_concept_id)
            target = states.get(edge.target_concept_id)
            prerequisite_mastery = prerequisite.mastery if prerequisite else 0
            target_mastery = target.mastery if target else 0
            if target_mastery > 0 and prerequisite_mastery + 10 < target_mastery:
                gaps.add(edge.source_concept_id)
        return gaps

    def _require_workspace(self, workspace_id: UUID) -> None:
        workspace = self.db.scalar(
            select(Workspace.id).where(
                Workspace.id == workspace_id,
                Workspace.user_id == self.user_id,
            )
        )
        if not workspace:
            raise AppError(404, "WORKSPACE_NOT_FOUND", "Workspace was not found.")
