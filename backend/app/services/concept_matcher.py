import math
import re
import unicodedata
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.concept import Concept, ConceptAlias
from app.schemas.concept import ExtractedConcept, MergeDecision
from app.services.ai.providers import AIProvider

PROMPT_DIR = Path(__file__).parent.parent / "prompts"


class ConceptMatcher:
    def __init__(self, db: Session, provider: AIProvider) -> None:
        self.db = db
        self.provider = provider

    def match_or_create(self, workspace_id: UUID, candidate: ExtractedConcept) -> Concept:
        normalized_name = normalize_concept_name(candidate.name)
        exact = self.db.scalar(
            select(Concept).where(
                Concept.workspace_id == workspace_id,
                Concept.normalized_name == normalized_name,
            )
        )
        if exact:
            self._strengthen(exact, candidate)
            return exact

        alias = self.db.scalar(
            select(Concept)
            .join(ConceptAlias)
            .where(
                Concept.workspace_id == workspace_id,
                ConceptAlias.normalized_alias == normalized_name,
            )
        )
        if alias:
            self._strengthen(alias, candidate)
            return alias

        embedding = self._safe_embed(f"{candidate.name}: {candidate.description}")
        semantic_match = self._semantic_match(workspace_id, candidate, embedding)
        if semantic_match:
            self._strengthen(semantic_match, candidate)
            return semantic_match

        concept = Concept(
            workspace_id=workspace_id,
            name=candidate.name.strip(),
            normalized_name=normalized_name,
            description=candidate.description.strip(),
            type=candidate.type.strip().lower(),
            importance=candidate.importance,
            confidence=candidate.confidence,
            embedding=embedding,
        )
        self.db.add(concept)
        self.db.flush()
        return concept

    def add_aliases(self, concept: Concept, aliases: list[str]) -> None:
        existing = {item.normalized_alias for item in concept.aliases}
        for value in aliases:
            normalized = normalize_concept_name(value)
            if not normalized or normalized in existing or normalized == concept.normalized_name:
                continue
            self.db.add(
                ConceptAlias(
                    concept_id=concept.id,
                    alias=value.strip(),
                    normalized_alias=normalized,
                )
            )
            existing.add(normalized)

    def _semantic_match(
        self,
        workspace_id: UUID,
        candidate: ExtractedConcept,
        embedding: list[float] | None,
    ) -> Concept | None:
        if not embedding:
            return None
        concepts = self.db.scalars(
            select(Concept).where(
                Concept.workspace_id == workspace_id,
                Concept.embedding.is_not(None),
            )
        )
        ranked = sorted(
            (
                (cosine_similarity(embedding, concept.embedding or []), concept)
                for concept in concepts
            ),
            key=lambda item: item[0],
            reverse=True,
        )
        if not ranked:
            return None
        similarity, concept = ranked[0]
        if similarity >= 0.92:
            return concept
        if similarity < 0.84:
            return None

        template = (PROMPT_DIR / "concept_merge_v1.txt").read_text()
        prompt = template.format(
            existing_name=concept.name,
            existing_description=concept.description,
            new_name=candidate.name,
            new_description=candidate.description,
        )
        decision = self.provider.generate_structured(prompt, MergeDecision)
        return concept if decision.same_concept else None

    def _safe_embed(self, text: str) -> list[float] | None:
        try:
            return self.provider.embed(text)
        except Exception:
            return None

    def _strengthen(self, concept: Concept, candidate: ExtractedConcept) -> None:
        if concept.type == "demo_concept":
            concept.name = candidate.name.strip()
            concept.normalized_name = normalize_concept_name(candidate.name)
            concept.description = candidate.description.strip()
            concept.type = candidate.type.strip().lower()
            concept.embedding = self._safe_embed(f"{candidate.name}: {candidate.description}")
        concept.importance = max(concept.importance, candidate.importance)
        concept.confidence = max(concept.confidence, candidate.confidence)
        if not concept.description and candidate.description:
            concept.description = candidate.description.strip()


def normalize_concept_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold().strip()
    return re.sub(r"[^\w]+", " ", normalized).strip()


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or len(left) != len(right):
        return 0.0
    magnitude = math.sqrt(sum(value * value for value in left)) * math.sqrt(
        sum(value * value for value in right)
    )
    return sum(a * b for a, b in zip(left, right, strict=True)) / magnitude if magnitude else 0.0
