from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.concept import Concept, ConceptSource
from app.models.learning import KnowledgeState, LearningPathItem, QuizAttempt, QuizQuestion
from app.models.source import Chunk
from app.models.workspace import Workspace
from app.schemas.learning import (
    QuizGenerationOutput,
    QuizQuestionRead,
    QuizResultRead,
)
from app.services.ai.providers import AIProvider
from app.services.content_language import language_instructions
from app.services.learning import knowledge_status, normalize_answer

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "quiz_generation_v1.txt"


class QuizService:
    def __init__(self, db: Session, user_id: UUID) -> None:
        self.db = db
        self.user_id = user_id

    def generate(self, concept_id: UUID, provider: AIProvider) -> list[QuizQuestionRead]:
        concept = self._require_concept(concept_id)
        chunks = list(
            self.db.scalars(
                select(Chunk)
                .join(ConceptSource)
                .where(ConceptSource.concept_id == concept.id)
                .order_by(Chunk.position)
                .limit(8)
            )
        )
        if not chunks:
            raise AppError(409, "CONCEPT_HAS_NO_EVIDENCE", "This concept has no source evidence.")
        context = "\n\n".join(f"[{chunk.id}] {chunk.content}" for chunk in chunks)
        prompt = PROMPT_PATH.read_text().format(
            concept_name=concept.name,
            description=concept.description,
            context=context,
        )
        source_ids = list({chunk.document.source_id for chunk in chunks})
        prompt = language_instructions(self.db, source_ids) + "\n" + prompt
        try:
            output = provider.generate_structured(prompt, QuizGenerationOutput)
        except Exception as error:
            raise AppError(
                503,
                "AI_PROVIDER_FAILED",
                "The AI provider could not create a quiz.",
            ) from error
        allowed_chunk_ids = {str(chunk.id) for chunk in chunks}
        questions: list[QuizQuestion] = []
        for draft in output.questions:
            cited = [str(chunk_id) for chunk_id in draft.source_chunk_ids]
            valid_citations = [chunk_id for chunk_id in cited if chunk_id in allowed_chunk_ids]
            if not valid_citations:
                valid_citations = [str(chunks[0].id)]
            question = QuizQuestion(
                concept_id=concept.id,
                question=draft.question,
                type=draft.type,
                choices=draft.choices,
                answer=draft.answer,
                explanation=draft.explanation,
                difficulty=draft.difficulty,
                source_chunk_ids=valid_citations,
                created_at=datetime.now(UTC),
            )
            self.db.add(question)
            questions.append(question)
        self.db.commit()
        return [question_response(question) for question in questions]

    def list_for_concept(self, concept_id: UUID) -> list[QuizQuestionRead]:
        self._require_concept(concept_id)
        questions = self.db.scalars(
            select(QuizQuestion)
            .where(QuizQuestion.concept_id == concept_id)
            .order_by(QuizQuestion.created_at.desc())
        )
        return [question_response(question) for question in questions]

    def answer(self, question_id: UUID, submitted_answer: str) -> QuizResultRead:
        question = self.db.scalar(
            select(QuizQuestion)
            .join(Concept)
            .join(Workspace)
            .where(QuizQuestion.id == question_id, Workspace.user_id == self.user_id)
        )
        if not question:
            raise AppError(404, "QUIZ_QUESTION_NOT_FOUND", "Quiz question was not found.")
        correct = is_correct_answer(question, submitted_answer)
        state = self._get_or_create_state(question.concept_id)
        mastery_before = state.mastery
        score = 100.0 if correct else 0.0
        state.mastery = round(mastery_before * 0.8 + score * 0.2, 2)
        state.confidence = min(1.0, state.confidence * 0.8 + 0.2)
        state.status = knowledge_status(state.mastery)
        state.last_reviewed_at = datetime.now(UTC)
        if state.mastery >= 85:
            for item in self.db.scalars(
                select(LearningPathItem).where(LearningPathItem.concept_id == question.concept_id)
            ):
                item.status = "completed"
        self.db.add(
            QuizAttempt(
                user_id=self.user_id,
                question_id=question.id,
                submitted_answer=submitted_answer,
                is_correct=correct,
                score=score,
                mastery_before=mastery_before,
                mastery_after=state.mastery,
                created_at=datetime.now(UTC),
            )
        )
        self.db.commit()
        return QuizResultRead(
            correct=correct,
            score=round(score),
            correct_answer=question.answer,
            explanation=question.explanation,
            mastery_before=round(mastery_before),
            mastery_after=round(state.mastery),
            knowledge_status=state.status,
        )

    def set_manual_status(self, concept_id: UUID, status: str) -> KnowledgeState:
        self._require_concept(concept_id)
        state = self._get_or_create_state(concept_id)
        state.status = status
        state.mastery = {"unseen": 0, "learning": 30, "understood": 70, "mastered": 90}[status]
        state.confidence = max(state.confidence, 0.6)
        state.last_reviewed_at = datetime.now(UTC)
        for item in self.db.scalars(
            select(LearningPathItem).where(LearningPathItem.concept_id == concept_id)
        ):
            item.status = "completed" if state.mastery >= 85 else "pending"
        self.db.commit()
        return state

    def _get_or_create_state(self, concept_id: UUID) -> KnowledgeState:
        state = self.db.scalar(
            select(KnowledgeState).where(
                KnowledgeState.user_id == self.user_id,
                KnowledgeState.concept_id == concept_id,
            )
        )
        if not state:
            state = KnowledgeState(user_id=self.user_id, concept_id=concept_id)
            self.db.add(state)
            self.db.flush()
        return state

    def _require_concept(self, concept_id: UUID) -> Concept:
        concept = self.db.scalar(
            select(Concept)
            .join(Workspace)
            .where(Concept.id == concept_id, Workspace.user_id == self.user_id)
        )
        if not concept:
            raise AppError(404, "CONCEPT_NOT_FOUND", "Concept was not found.")
        return concept


def question_response(question: QuizQuestion) -> QuizQuestionRead:
    return QuizQuestionRead(
        id=question.id,
        concept_id=question.concept_id,
        question=question.question,
        type=question.type,
        choices=question.choices,
        difficulty=question.difficulty,
        source_chunk_ids=[UUID(value) for value in question.source_chunk_ids],
    )


def is_correct_answer(question: QuizQuestion, submitted_answer: str) -> bool:
    expected = normalize_answer(question.answer)
    submitted = normalize_answer(submitted_answer)
    if question.type == "multiple_choice" or expected == submitted:
        return expected == submitted
    expected_terms = set(expected.split())
    submitted_terms = set(submitted.split())
    overlap = len(expected_terms & submitted_terms) / len(expected_terms) if expected_terms else 0
    return overlap >= 0.7
