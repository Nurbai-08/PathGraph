import re
from collections import Counter
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.concept import Concept, ConceptEdge, ConceptSource
from app.models.source import Chunk, Document, Source
from app.services.concept_matcher import normalize_concept_name

WORD_PATTERN = re.compile(r"[^\W\d_][\w-]{4,}", re.UNICODE)
STOP_WORDS = {
    "about",
    "after",
    "also",
    "before",
    "being",
    "between",
    "could",
    "from",
    "have",
    "into",
    "other",
    "their",
    "these",
    "this",
    "using",
    "which",
    "with",
    "более",
    "будет",
    "были",
    "когда",
    "которые",
    "может",
    "после",
    "также",
    "этого",
    "этот",
}
MAX_CONCEPTS = 24


class DemoConceptExtractor:
    def __init__(self, db: Session) -> None:
        self.db = db

    def run(self, source_id: UUID) -> int:
        source = self.db.get(Source, source_id)
        if not source:
            return 0
        concepts: list[Concept] = []
        for chunk in self._chunks(source_id):
            for name in self._candidate_names(chunk):
                concept = self._upsert_concept(source, chunk, name)
                if concept not in concepts:
                    concepts.append(concept)
                if len(concepts) >= MAX_CONCEPTS:
                    break
            if len(concepts) >= MAX_CONCEPTS:
                break
        self._connect(source.workspace_id, concepts)
        self.db.commit()
        return len(concepts)

    def _upsert_concept(self, source: Source, chunk: Chunk, name: str) -> Concept:
        normalized = normalize_concept_name(name)
        concept = self.db.scalar(
            select(Concept).where(
                Concept.workspace_id == source.workspace_id,
                Concept.normalized_name == normalized,
            )
        )
        if not concept:
            concept = Concept(
                workspace_id=source.workspace_id,
                name=name,
                normalized_name=normalized,
                description=chunk.content[:500],
                type="demo_concept",
                importance=0.5,
                confidence=0.45,
            )
            self.db.add(concept)
            self.db.flush()
        evidence = self.db.scalar(
            select(ConceptSource).where(
                ConceptSource.concept_id == concept.id,
                ConceptSource.source_id == source.id,
                ConceptSource.chunk_id == chunk.id,
            )
        )
        if not evidence:
            self.db.add(
                ConceptSource(
                    concept_id=concept.id,
                    source_id=source.id,
                    chunk_id=chunk.id,
                    confidence=0.45,
                )
            )
        return concept

    def _connect(self, workspace_id: UUID, concepts: list[Concept]) -> None:
        for left, right in zip(concepts, concepts[1:], strict=False):
            edge = self.db.scalar(
                select(ConceptEdge).where(
                    ConceptEdge.workspace_id == workspace_id,
                    ConceptEdge.source_concept_id == left.id,
                    ConceptEdge.target_concept_id == right.id,
                    ConceptEdge.relation_type == "related_to",
                )
            )
            if not edge:
                self.db.add(
                    ConceptEdge(
                        workspace_id=workspace_id,
                        source_concept_id=left.id,
                        target_concept_id=right.id,
                        relation_type="related_to",
                        confidence=0.4,
                    )
                )

    def _chunks(self, source_id: UUID) -> list[Chunk]:
        document = self.db.scalar(
            select(Document)
            .options(selectinload(Document.chunks))
            .where(Document.source_id == source_id)
            .order_by(Document.version.desc())
        )
        return sorted(document.chunks, key=lambda item: item.position) if document else []

    def _candidate_names(self, chunk: Chunk) -> list[str]:
        candidates: list[str] = []
        heading = (chunk.heading_path or "").split(" > ")[-1].strip("# ")
        if heading and heading.casefold() != "root":
            candidates.append(heading[:200])
        words = (
            word.casefold()
            for word in WORD_PATTERN.findall(chunk.content)
            if word.casefold() not in STOP_WORDS
        )
        candidates.extend(word.title() for word, _ in Counter(words).most_common(2))
        return list(dict.fromkeys(value for value in candidates if value))
