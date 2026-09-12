from __future__ import annotations

import re
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError
from app.models.concept import Concept, ConceptEdge
from app.models.learning import KnowledgeState, LearningPath, LearningPathItem
from app.models.workspace import Workspace
from app.schemas.learning import (
    KnowledgeGapRead,
    LearningConceptRead,
    LearningPathCreate,
    LearningPathItemRead,
    LearningPathRead,
    NextConceptRead,
)
from app.services.concept_matcher import normalize_concept_name


class LearningPathService:
    def __init__(self, db: Session, user_id: UUID) -> None:
        self.db = db
        self.user_id = user_id

    def create(self, workspace_id: UUID, payload: LearningPathCreate) -> LearningPathRead:
        self._require_workspace(workspace_id)
        concepts = list(
            self.db.scalars(select(Concept).where(Concept.workspace_id == workspace_id))
        )
        if not concepts:
            raise AppError(409, "GRAPH_EMPTY", "Analyze sources before creating a learning path.")
        goals = select_goal_concepts(concepts, payload.goal)
        ordered = self._ordered_with_prerequisites(workspace_id, goals)
        states = self._state_map([concept.id for concept in ordered])

        learning_path = LearningPath(
            workspace_id=workspace_id,
            title=(payload.title or payload.goal).strip()[:160],
            goal=payload.goal.strip(),
            status="active",
            created_at=datetime.now(UTC),
        )
        self.db.add(learning_path)
        self.db.flush()
        for position, concept in enumerate(ordered):
            state = states.get(concept.id)
            self.db.add(
                LearningPathItem(
                    learning_path_id=learning_path.id,
                    concept_id=concept.id,
                    position=position,
                    status="completed" if state and state.mastery >= 85 else "pending",
                )
            )
        self.db.commit()
        return self.get(learning_path.id)

    def list(self, workspace_id: UUID) -> list[LearningPathRead]:
        self._require_workspace(workspace_id)
        paths = self.db.scalars(
            select(LearningPath)
            .where(LearningPath.workspace_id == workspace_id)
            .order_by(LearningPath.created_at.desc())
        )
        return [self.get(path.id) for path in paths]

    def get(self, path_id: UUID) -> LearningPathRead:
        learning_path = self._require_path(path_id)
        items = list(
            self.db.scalars(
                select(LearningPathItem)
                .where(LearningPathItem.learning_path_id == path_id)
                .order_by(LearningPathItem.position)
            )
        )
        concepts = {
            concept.id: concept
            for concept in self.db.scalars(
                select(Concept).where(Concept.id.in_([item.concept_id for item in items]))
            )
        }
        states = self._state_map(list(concepts))
        return LearningPathRead(
            id=learning_path.id,
            workspace_id=learning_path.workspace_id,
            title=learning_path.title,
            goal=learning_path.goal,
            status=learning_path.status,
            created_at=learning_path.created_at,
            items=[
                LearningPathItemRead(
                    id=item.id,
                    position=item.position,
                    status=item.status,
                    concept=concept_response(
                        concepts[item.concept_id], states.get(item.concept_id)
                    ),
                )
                for item in items
            ],
        )

    def next_concept(self, path_id: UUID) -> NextConceptRead:
        detail = self.get(path_id)
        concept_ids = [item.concept.id for item in detail.items]
        concepts = {
            concept.id: concept
            for concept in self.db.scalars(select(Concept).where(Concept.id.in_(concept_ids)))
        }
        states = self._state_map(concept_ids)
        edges = list(
            self.db.scalars(
                select(ConceptEdge).where(
                    ConceptEdge.workspace_id == detail.workspace_id,
                    ConceptEdge.relation_type == "prerequisite_of",
                    ConceptEdge.target_concept_id.in_(concept_ids),
                )
            )
        )
        prerequisites: dict[UUID, list[UUID]] = {}
        for edge in edges:
            prerequisites.setdefault(edge.target_concept_id, []).append(edge.source_concept_id)

        available: list[Concept] = []
        gaps: list[KnowledgeGapRead] = []
        for item in detail.items:
            state = states.get(item.concept.id)
            if state and state.mastery >= 85:
                self._complete_path_item(path_id, item.concept.id)
                continue
            unfinished = [
                prerequisite_id
                for prerequisite_id in prerequisites.get(item.concept.id, [])
                if states.get(prerequisite_id) is None or states[prerequisite_id].mastery < 60
            ]
            if not unfinished:
                available.append(concepts[item.concept.id])
            for prerequisite_id in unfinished:
                prerequisite = concepts.get(prerequisite_id)
                if prerequisite:
                    gaps.append(
                        KnowledgeGapRead(
                            concept=concept_response(prerequisite, states.get(prerequisite_id)),
                            blocked_concept=item.concept,
                            message=(
                                f"Review {prerequisite.name} before continuing {item.concept.name}."
                            ),
                        )
                    )
        self.db.commit()
        available.sort(key=lambda concept: concept.importance, reverse=True)
        selected = available[0] if available else None
        return NextConceptRead(
            concept=concept_response(selected, states.get(selected.id)) if selected else None,
            gaps=gaps[:5],
        )

    def _ordered_with_prerequisites(
        self, workspace_id: UUID, goals: list[Concept]
    ) -> list[Concept]:
        concepts = {
            concept.id: concept
            for concept in self.db.scalars(
                select(Concept).where(Concept.workspace_id == workspace_id)
            )
        }
        edges = self.db.scalars(
            select(ConceptEdge).where(
                ConceptEdge.workspace_id == workspace_id,
                ConceptEdge.relation_type == "prerequisite_of",
            )
        )
        prerequisites: dict[UUID, list[UUID]] = {}
        for edge in edges:
            prerequisites.setdefault(edge.target_concept_id, []).append(edge.source_concept_id)
        ordered: list[Concept] = []
        visited: set[UUID] = set()

        def visit(concept_id: UUID) -> None:
            if concept_id in visited:
                return
            visited.add(concept_id)
            for prerequisite_id in prerequisites.get(concept_id, []):
                visit(prerequisite_id)
            if concept_id in concepts:
                ordered.append(concepts[concept_id])

        for goal in sorted(goals, key=lambda item: item.importance, reverse=True):
            visit(goal.id)
        return ordered

    def _state_map(self, concept_ids: list[UUID]) -> dict[UUID, KnowledgeState]:
        if not concept_ids:
            return {}
        states = self.db.scalars(
            select(KnowledgeState).where(
                KnowledgeState.user_id == self.user_id,
                KnowledgeState.concept_id.in_(concept_ids),
            )
        )
        return {state.concept_id: state for state in states}

    def _complete_path_item(self, path_id: UUID, concept_id: UUID) -> None:
        item = self.db.scalar(
            select(LearningPathItem).where(
                LearningPathItem.learning_path_id == path_id,
                LearningPathItem.concept_id == concept_id,
            )
        )
        if item:
            item.status = "completed"

    def _require_workspace(self, workspace_id: UUID) -> Workspace:
        workspace = self.db.scalar(
            select(Workspace).where(
                Workspace.id == workspace_id,
                Workspace.user_id == self.user_id,
            )
        )
        if not workspace:
            raise AppError(404, "WORKSPACE_NOT_FOUND", "Workspace was not found.")
        return workspace

    def _require_path(self, path_id: UUID) -> LearningPath:
        learning_path = self.db.scalar(
            select(LearningPath)
            .join(Workspace)
            .options(selectinload(LearningPath.items))
            .where(LearningPath.id == path_id, Workspace.user_id == self.user_id)
        )
        if not learning_path:
            raise AppError(404, "LEARNING_PATH_NOT_FOUND", "Learning path was not found.")
        return learning_path


def select_goal_concepts(concepts: list[Concept], goal: str) -> list[Concept]:
    goal_terms = set(normalize_concept_name(goal).split()) - {
        "i",
        "want",
        "to",
        "learn",
        "understand",
    }
    ranked: list[tuple[int, float, Concept]] = []
    for concept in concepts:
        name_terms = set(concept.normalized_name.split())
        description_terms = set(normalize_concept_name(concept.description).split())
        score = len(goal_terms & name_terms) * 5 + len(goal_terms & description_terms)
        ranked.append((score, concept.importance, concept))
    matches = [
        item[2] for item in sorted(ranked, reverse=True, key=lambda item: item[:2]) if item[0]
    ]
    return matches[:3] or sorted(concepts, key=lambda item: item.importance, reverse=True)[:1]


def concept_response(concept: Concept | None, state: KnowledgeState | None) -> LearningConceptRead:
    if concept is None:
        raise ValueError("Concept is required.")
    mastery = round(state.mastery) if state else 0
    return LearningConceptRead(
        id=concept.id,
        name=concept.name,
        type=concept.type,
        importance=round(concept.importance * 100),
        status=knowledge_status(mastery),
        mastery=mastery,
    )


def knowledge_status(mastery: float) -> str:
    if mastery >= 85:
        return "mastered"
    if mastery >= 60:
        return "understood"
    if mastery > 0:
        return "learning"
    return "unseen"


def normalize_answer(value: str) -> str:
    return re.sub(r"[^\w]+", " ", value.casefold()).strip()
