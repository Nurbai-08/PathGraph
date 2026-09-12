from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.errors import AppError
from app.models.ai import AIRun, AISetting
from app.models.concept import Concept, ConceptSource
from app.models.source import Chunk, Document, Source
from app.models.workspace import Workspace
from app.schemas.concept import ConceptExtractionOutput
from app.services.ai.factory import create_provider
from app.services.ai.providers import AIProvider
from app.services.concept_graph import ConceptGraphService
from app.services.concept_matcher import ConceptMatcher, normalize_concept_name
from app.services.content_language import language_instructions

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "concept_extraction_v1.txt"
MAX_ANALYSIS_CHUNKS = 24
MAX_CHUNK_PROMPT_CHARS = 12_000


class ConceptExtractionService:
    def __init__(self, db: Session, provider: AIProvider) -> None:
        self.db = db
        self.provider = provider

    def run(self, source_id: UUID, job_id: UUID | None = None) -> int:
        source = self.db.get(Source, source_id)
        if not source or source.status not in {"ready", "processing"}:
            raise AppError(409, "SOURCE_NOT_READY", "The source must be ready before analysis.")
        chunks = self._latest_chunks(source.id)
        matcher = ConceptMatcher(self.db, self.provider)
        graph = ConceptGraphService(self.db, source.workspace_id)
        concept_ids: set[UUID] = set()
        failed_chunks = 0

        for chunk in chunks:
            if not chunk.embedding:
                try:
                    chunk.embedding = self.provider.embed(chunk.content)
                    self.db.commit()
                except Exception:
                    self.db.rollback()
            output = self._extract_chunk(chunk, job_id)
            if not output:
                failed_chunks += 1
                continue
            concepts_by_name: dict[str, Concept] = {}
            for candidate in output.concepts:
                concept = matcher.match_or_create(source.workspace_id, candidate)
                matcher.add_aliases(concept, candidate.aliases)
                self._add_evidence(concept, source, chunk, candidate.confidence)
                concepts_by_name[normalize_concept_name(candidate.name)] = concept
                for alias in candidate.aliases:
                    concepts_by_name[normalize_concept_name(alias)] = concept
                concept_ids.add(concept.id)

            for relation in output.relationships:
                source_concept = concepts_by_name.get(normalize_concept_name(relation.source_name))
                target_concept = concepts_by_name.get(normalize_concept_name(relation.target_name))
                if not source_concept or not target_concept:
                    continue
                try:
                    graph.add_edge(
                        source_concept.id,
                        target_concept.id,
                        relation.relation_type,
                        relation.confidence,
                    )
                except AppError:
                    continue
            self.db.commit()
        if failed_chunks and not concept_ids:
            raise AppError(
                503, "AI_ANALYSIS_FAILED", "AI analysis failed. Check the provider and retry."
            )
        if not concept_ids:
            raise AppError(
                422,
                "NO_CONCEPTS_FOUND",
                "No learning concepts found. Add a lesson or article instead of a navigation page.",
            )
        self._remove_demo_evidence(source.id)
        return len(concept_ids)

    def _remove_demo_evidence(self, source_id: UUID) -> None:
        evidence = list(
            self.db.scalars(
                select(ConceptSource)
                .join(Concept)
                .where(
                    ConceptSource.source_id == source_id,
                    Concept.type == "demo_concept",
                )
            )
        )
        concept_ids = {item.concept_id for item in evidence}
        if evidence:
            self.db.execute(
                delete(ConceptSource).where(ConceptSource.id.in_([item.id for item in evidence]))
            )
            self.db.flush()
        for concept_id in concept_ids:
            concept = self.db.get(Concept, concept_id)
            has_evidence = self.db.scalar(
                select(ConceptSource.id).where(ConceptSource.concept_id == concept_id).limit(1)
            )
            if concept and not concept.is_manual and not has_evidence:
                self.db.delete(concept)
        self.db.commit()

    def _extract_chunk(self, chunk: Chunk, job_id: UUID | None) -> ConceptExtractionOutput | None:
        template = PROMPT_PATH.read_text()
        prompt = template.format(
            heading_path=chunk.heading_path or "Root",
            content=chunk.content[:MAX_CHUNK_PROMPT_CHARS],
        )
        prompt = language_instructions(self.db, [chunk.document.source_id]) + "\n" + prompt
        started = perf_counter()
        try:
            output = self.provider.generate_structured(prompt, ConceptExtractionOutput)
            self._record_run(
                job_id,
                "completed",
                prompt,
                output.model_dump_json(),
                started,
            )
            return output
        except Exception as error:
            self.db.rollback()
            self._record_run(job_id, "failed", prompt, "", started, str(error)[:1000])
            return None

    def _record_run(
        self,
        job_id: UUID | None,
        status: str,
        prompt: str,
        output: str,
        started: float,
        error: str | None = None,
    ) -> None:
        self.db.add(
            AIRun(
                job_id=job_id,
                provider=self.provider.provider_name,
                model=self.provider.model,
                operation="concept_extraction",
                status=status,
                input_tokens=estimate_tokens(prompt),
                output_tokens=estimate_tokens(output),
                duration_ms=round((perf_counter() - started) * 1000),
                error=error,
                created_at=datetime.now(UTC),
            )
        )
        self.db.commit()

    def _latest_chunks(self, source_id: UUID) -> list[Chunk]:
        document = self.db.scalar(
            select(Document)
            .options(selectinload(Document.chunks))
            .where(Document.source_id == source_id)
            .order_by(Document.version.desc())
        )
        if not document:
            return []
        return sorted(document.chunks, key=lambda chunk: chunk.position)[:MAX_ANALYSIS_CHUNKS]

    def _add_evidence(
        self, concept: Concept, source: Source, chunk: Chunk, confidence: float
    ) -> None:
        evidence = self.db.scalar(
            select(ConceptSource).where(
                ConceptSource.concept_id == concept.id,
                ConceptSource.source_id == source.id,
                ConceptSource.chunk_id == chunk.id,
            )
        )
        if evidence:
            evidence.confidence = max(evidence.confidence, confidence)
            return
        self.db.add(
            ConceptSource(
                concept_id=concept.id,
                source_id=source.id,
                chunk_id=chunk.id,
                confidence=confidence,
                created_at=datetime.now(UTC),
            )
        )


def analyze_source_if_configured(db: Session, source_id: UUID, job_id: UUID) -> int:
    setting = db.scalar(
        select(AISetting)
        .join(Workspace, Workspace.user_id == AISetting.user_id)
        .join(Source, Source.workspace_id == Workspace.id)
        .where(Source.id == source_id)
    )
    if not setting:
        if settings.demo_graph_enabled:
            from app.services.demo_concept_extraction import DemoConceptExtractor

            return DemoConceptExtractor(db).run(source_id)
        return 0
    return ConceptExtractionService(db, create_provider(setting)).run(source_id, job_id)


def analyze_source_task(source_id: UUID, job_id: UUID | None = None) -> None:
    with SessionLocal() as db:
        source = db.get(Source, source_id)
        if not source:
            return
        setting = db.scalar(
            select(AISetting)
            .join(Workspace, Workspace.user_id == AISetting.user_id)
            .where(Workspace.id == source.workspace_id)
        )
        if not setting:
            return
        ConceptExtractionService(db, create_provider(setting)).run(source_id, job_id)


def estimate_tokens(content: str) -> int:
    return max(0, round(len(content.split()) * 1.3))
