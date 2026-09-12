from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.ai import AIRun
from app.models.concept import Concept, ConceptEdge
from app.models.workspace import Workspace
from app.schemas.interactions import (
    CompareAnswerRead,
    CompareGeneration,
    GroundedAnswerRead,
    GroundedGeneration,
    WhyAnswerRead,
    WhyGeneration,
)
from app.services.ai.providers import AIProvider
from app.services.content_language import language_instructions
from app.services.context_builder import BuiltContext, ContextBuilder
from app.services.graph_query import GraphQueryService

PROMPT_DIR = Path(__file__).parent.parent / "prompts"


class InteractionService:
    def __init__(self, db: Session, user_id: UUID, provider: AIProvider) -> None:
        self.db = db
        self.user_id = user_id
        self.provider = provider
        self.context_builder = ContextBuilder(db, user_id, provider)

    def explain(self, concept_id: UUID, mode: str) -> GroundedAnswerRead:
        concept = self._require_concept(concept_id)
        detail = GraphQueryService(self.db, self.user_id).concept_detail(concept.id)
        query = f"Explain {concept.name} {concept.description}"
        context = self.context_builder.build(concept.workspace_id, query, [concept.id])
        prompt = self._prompt("explain_v1.txt").format(
            concept_name=concept.name,
            mastery=detail.mastery,
            mode=mode,
            prerequisites=", ".join(item.name for item in detail.prerequisites) or "None",
            context=context.text or "No source excerpts available.",
        )
        generated = self._generate(self._localized(prompt, context), GroundedGeneration, "explain")
        return grounded_response(generated, context)

    def why(self, concept_id: UUID) -> WhyAnswerRead:
        concept = self._require_concept(concept_id)
        path = self._downstream_path(concept)
        context = self.context_builder.build(
            concept.workspace_id,
            f"Why learn {' then '.join(path)}?",
            [concept.id],
        )
        prompt = self._prompt("why_v1.txt").format(
            concept_name=concept.name,
            path=" → ".join(path),
            context=context.text or "No source excerpts available.",
        )
        generated = self._generate(self._localized(prompt, context), WhyGeneration, "why_concept")
        base = grounded_response(generated, context)
        return WhyAnswerRead(
            **base.model_dump(),
            why_it_matters=generated.why_it_matters,
            path=path,
        )

    def compare(
        self, workspace_id: UUID, concept_a_id: UUID, concept_b_id: UUID
    ) -> CompareAnswerRead:
        concept_a = self._require_concept(concept_a_id, workspace_id)
        concept_b = self._require_concept(concept_b_id, workspace_id)
        context = self.context_builder.build(
            workspace_id,
            f"Compare {concept_a.name} and {concept_b.name}",
            [concept_a.id, concept_b.id],
        )
        prompt = self._prompt("compare_v1.txt").format(
            concept_a=concept_a.name,
            concept_b=concept_b.name,
            context=context.text or "No source excerpts available.",
        )
        generated = self._generate(
            self._localized(prompt, context), CompareGeneration, "compare_concepts"
        )
        return CompareAnswerRead(
            concept_a=concept_a.name,
            concept_b=concept_b.name,
            similarities=generated.similarities,
            differences=generated.differences,
            when_to_use_a=generated.when_to_use_a,
            when_to_use_b=generated.when_to_use_b,
            examples=generated.examples,
            citations=filter_citations(generated.citation_indices, context),
        )

    def chat(self, workspace_id: UUID, question: str) -> GroundedAnswerRead:
        context = self.context_builder.build(workspace_id, question)
        neighbors = self._neighbor_context(workspace_id, context.concept_names)
        prompt = self._prompt("chat_v1.txt").format(
            question=question,
            concepts="; ".join(context.concept_names + neighbors) or "None found",
            context=context.text or "No source excerpts available.",
        )
        generated = self._generate(
            self._localized(prompt, context), GroundedGeneration, "graph_chat"
        )
        return grounded_response(generated, context)

    def _localized(self, prompt: str, context: BuiltContext) -> str:
        source_ids = list({citation.source_id for citation in context.citations})
        return language_instructions(self.db, source_ids) + "\n" + prompt

    def _generate(self, prompt: str, schema: type[BaseModel], operation: str):
        started = perf_counter()
        try:
            result = self.provider.generate_structured(prompt, schema)
        except Exception as error:
            self._record_run(operation, "failed", prompt, "", started, str(error)[:1000])
            raise AppError(
                503, "AI_PROVIDER_FAILED", "The AI provider could not answer."
            ) from error
        self._record_run(operation, "completed", prompt, result.model_dump_json(), started)
        return result

    def _record_run(
        self,
        operation: str,
        status: str,
        prompt: str,
        output: str,
        started: float,
        error: str | None = None,
    ) -> None:
        self.db.add(
            AIRun(
                provider=self.provider.provider_name,
                model=self.provider.model,
                operation=operation,
                status=status,
                input_tokens=round(len(prompt.split()) * 1.3),
                output_tokens=round(len(output.split()) * 1.3),
                duration_ms=round((perf_counter() - started) * 1000),
                error=error,
                created_at=datetime.now(UTC),
            )
        )
        self.db.commit()

    def _downstream_path(self, concept: Concept) -> list[str]:
        path = [concept.name]
        current_id = concept.id
        visited = {concept.id}
        for _ in range(3):
            candidates = list(
                self.db.scalars(
                    select(Concept)
                    .join(ConceptEdge, Concept.id == ConceptEdge.target_concept_id)
                    .where(
                        ConceptEdge.workspace_id == concept.workspace_id,
                        ConceptEdge.source_concept_id == current_id,
                        Concept.id.not_in(visited),
                    )
                    .order_by(Concept.importance.desc())
                )
            )
            if not candidates:
                break
            current = candidates[0]
            path.append(current.name)
            current_id = current.id
            visited.add(current.id)
        return path

    def _neighbor_context(self, workspace_id: UUID, names: list[str]) -> list[str]:
        if not names:
            return []
        concept_ids = list(
            self.db.scalars(
                select(Concept.id).where(
                    Concept.workspace_id == workspace_id,
                    Concept.name.in_(names),
                )
            )
        )
        return self.context_builder.graph_neighbors(workspace_id, concept_ids)

    def _require_concept(self, concept_id: UUID, workspace_id: UUID | None = None) -> Concept:
        query = (
            select(Concept)
            .join(Workspace)
            .where(Concept.id == concept_id, Workspace.user_id == self.user_id)
        )
        if workspace_id:
            query = query.where(Concept.workspace_id == workspace_id)
        concept = self.db.scalar(query)
        if not concept:
            raise AppError(404, "CONCEPT_NOT_FOUND", "Concept was not found.")
        return concept

    def _prompt(self, filename: str) -> str:
        return (PROMPT_DIR / filename).read_text()


def grounded_response(generated: GroundedGeneration, context: BuiltContext) -> GroundedAnswerRead:
    return GroundedAnswerRead(
        source_backed_answer=generated.source_backed_answer,
        additional_explanation=generated.additional_explanation,
        citations=filter_citations(generated.citation_indices, context),
    )


def filter_citations(indices: list[int], context: BuiltContext):
    requested = set(indices)
    return [citation for citation in context.citations if citation.index in requested]
