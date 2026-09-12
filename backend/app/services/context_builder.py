import re
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.concept import Concept, ConceptEdge, ConceptSource
from app.models.source import Chunk, Document, Source
from app.models.workspace import Workspace
from app.schemas.interactions import CitationRead
from app.services.ai.providers import AIProvider
from app.services.concept_matcher import cosine_similarity, normalize_concept_name

MAX_CONTEXT_CHUNKS = 6
MAX_CONTEXT_CHARACTERS = 12_000


@dataclass(slots=True)
class RetrievedChunk:
    chunk: Chunk
    source: Source
    score: float


@dataclass(slots=True)
class BuiltContext:
    text: str
    citations: list[CitationRead]
    concept_names: list[str]


class ContextBuilder:
    def __init__(self, db: Session, user_id: UUID, provider: AIProvider) -> None:
        self.db = db
        self.user_id = user_id
        self.provider = provider

    def build(
        self,
        workspace_id: UUID,
        query: str,
        preferred_concept_ids: list[UUID] | None = None,
    ) -> BuiltContext:
        self._require_workspace(workspace_id)
        chunks = self._workspace_chunks(workspace_id)
        preferred = set(preferred_concept_ids or [])
        preferred_chunk_ids = (
            set(
                self.db.scalars(
                    select(ConceptSource.chunk_id).where(ConceptSource.concept_id.in_(preferred))
                )
            )
            if preferred
            else set()
        )
        query_embedding = self._safe_embed(query)

        ranked = [
            RetrievedChunk(
                chunk=chunk,
                source=source,
                score=rank_chunk(chunk, query, query_embedding)
                + (2.0 if chunk.id in preferred_chunk_ids else 0.0),
            )
            for chunk, source in chunks
        ]
        ranked.sort(key=lambda item: item.score, reverse=True)
        selected = self._fit_context(ranked)
        citations = [
            CitationRead(
                index=index,
                source_id=item.source.id,
                source_title=item.source.title,
                chunk_id=item.chunk.id,
                heading_path=item.chunk.heading_path,
                excerpt=item.chunk.content[:600],
            )
            for index, item in enumerate(selected, start=1)
        ]
        text = "\n\n".join(
            f"[{citation.index}] Source: {citation.source_title}\n"
            f"Heading: {citation.heading_path or 'Root'}\n{citation.excerpt}"
            for citation in citations
        )
        concept_names = self._concept_names([item.chunk.id for item in selected])
        return BuiltContext(text=text, citations=citations, concept_names=concept_names)

    def graph_neighbors(self, workspace_id: UUID, concept_ids: list[UUID]) -> list[str]:
        if not concept_ids:
            return []
        edges = list(
            self.db.scalars(
                select(ConceptEdge)
                .where(
                    ConceptEdge.workspace_id == workspace_id,
                    or_(
                        ConceptEdge.source_concept_id.in_(concept_ids),
                        ConceptEdge.target_concept_id.in_(concept_ids),
                    ),
                )
                .limit(40)
            )
        )
        ids = {
            concept_id
            for edge in edges
            for concept_id in (edge.source_concept_id, edge.target_concept_id)
        }
        concepts = {
            concept.id: concept.name
            for concept in self.db.scalars(select(Concept).where(Concept.id.in_(ids)))
        }
        return [
            f"{concepts.get(edge.source_concept_id, '?')} {edge.relation_type} "
            f"{concepts.get(edge.target_concept_id, '?')}"
            for edge in edges
        ]

    def _workspace_chunks(self, workspace_id: UUID) -> list[tuple[Chunk, Source]]:
        return list(
            self.db.execute(
                select(Chunk, Source)
                .join(Document, Chunk.document_id == Document.id)
                .join(Source, Document.source_id == Source.id)
                .where(Source.workspace_id == workspace_id, Source.status == "ready")
            )
        )

    def _fit_context(self, ranked: list[RetrievedChunk]) -> list[RetrievedChunk]:
        selected: list[RetrievedChunk] = []
        character_count = 0
        for item in ranked:
            if len(selected) >= MAX_CONTEXT_CHUNKS:
                break
            if selected and character_count + len(item.chunk.content) > MAX_CONTEXT_CHARACTERS:
                continue
            selected.append(item)
            character_count += len(item.chunk.content)
        return selected

    def _concept_names(self, chunk_ids: list[UUID]) -> list[str]:
        if not chunk_ids:
            return []
        names = self.db.scalars(
            select(Concept.name)
            .join(ConceptSource)
            .where(ConceptSource.chunk_id.in_(chunk_ids))
            .distinct()
            .limit(20)
        )
        return list(names)

    def _safe_embed(self, query: str) -> list[float] | None:
        try:
            return self.provider.embed(query)
        except Exception:
            return None

    def _require_workspace(self, workspace_id: UUID) -> None:
        exists = self.db.scalar(
            select(Workspace.id).where(
                Workspace.id == workspace_id,
                Workspace.user_id == self.user_id,
            )
        )
        if not exists:
            raise AppError(404, "WORKSPACE_NOT_FOUND", "Workspace was not found.")


def rank_chunk(chunk: Chunk, query: str, query_embedding: list[float] | None) -> float:
    semantic = (
        cosine_similarity(query_embedding, chunk.embedding or [])
        if query_embedding and chunk.embedding
        else 0.0
    )
    query_terms = set(normalize_concept_name(query).split())
    content_terms = set(normalize_concept_name(chunk.content).split())
    lexical = len(query_terms & content_terms) / len(query_terms) if query_terms else 0.0
    heading_terms = set(re.findall(r"\w+", chunk.heading_path.casefold()))
    heading = len(query_terms & heading_terms) / len(query_terms) if query_terms else 0.0
    return semantic * 0.65 + lexical * 0.25 + heading * 0.1
