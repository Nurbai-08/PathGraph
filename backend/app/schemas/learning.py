from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class LearningPathCreate(BaseModel):
    goal: str = Field(min_length=3, max_length=2000)
    title: str | None = Field(default=None, min_length=1, max_length=160)


class LearningConceptRead(BaseModel):
    id: UUID
    name: str
    type: str
    importance: int
    status: Literal["unseen", "learning", "understood", "mastered"]
    mastery: int


class LearningPathItemRead(BaseModel):
    id: UUID
    position: int
    status: str
    concept: LearningConceptRead


class LearningPathRead(BaseModel):
    id: UUID
    workspace_id: UUID
    title: str
    goal: str
    status: str
    created_at: datetime
    items: list[LearningPathItemRead]


class KnowledgeGapRead(BaseModel):
    concept: LearningConceptRead
    blocked_concept: LearningConceptRead
    message: str


class NextConceptRead(BaseModel):
    concept: LearningConceptRead | None
    gaps: list[KnowledgeGapRead]


class KnowledgeStateUpdate(BaseModel):
    status: Literal["unseen", "learning", "understood", "mastered"]


class QuizQuestionDraft(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    type: Literal["multiple_choice", "short_answer"]
    choices: list[str] | None = Field(default=None, min_length=2, max_length=6)
    answer: str = Field(min_length=1, max_length=2000)
    explanation: str = Field(min_length=1, max_length=4000)
    difficulty: int = Field(ge=1, le=5)
    source_chunk_ids: list[UUID] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_choices(self) -> "QuizQuestionDraft":
        if self.type == "multiple_choice" and not self.choices:
            raise ValueError("Multiple-choice questions require choices.")
        if self.choices and self.answer not in self.choices:
            raise ValueError("The answer must be one of the choices.")
        return self


class QuizGenerationOutput(BaseModel):
    questions: list[QuizQuestionDraft] = Field(min_length=1, max_length=10)


class QuizQuestionRead(BaseModel):
    id: UUID
    concept_id: UUID
    question: str
    type: str
    choices: list[str] | None
    explanation: str | None = None
    difficulty: int
    source_chunk_ids: list[UUID]


class QuizAnswer(BaseModel):
    answer: str = Field(min_length=1, max_length=2000)


class QuizResultRead(BaseModel):
    correct: bool
    score: int
    correct_answer: str
    explanation: str
    mastery_before: int
    mastery_after: int
    knowledge_status: str
