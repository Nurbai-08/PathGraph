import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class KnowledgeState(TimestampMixin, Base):
    __tablename__ = "knowledge_states"
    __table_args__ = (
        UniqueConstraint("user_id", "concept_id", name="uq_knowledge_state_user_concept"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    concept_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("concepts.id", ondelete="CASCADE"), index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(String(16), default="unseen", nullable=False)
    mastery: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    last_reviewed_at: Mapped[datetime | None]


class LearningPath(Base):
    __tablename__ = "learning_paths"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("workspaces.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    created_at: Mapped[datetime]

    items: Mapped[list["LearningPathItem"]] = relationship(
        back_populates="learning_path", cascade="all, delete-orphan"
    )


class LearningPathItem(Base):
    __tablename__ = "learning_path_items"
    __table_args__ = (
        UniqueConstraint("learning_path_id", "concept_id", name="uq_learning_path_concept"),
        UniqueConstraint("learning_path_id", "position", name="uq_learning_path_position"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    learning_path_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("learning_paths.id", ondelete="CASCADE"), index=True, nullable=False
    )
    concept_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("concepts.id", ondelete="CASCADE"), index=True, nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)

    learning_path: Mapped[LearningPath] = relationship(back_populates="items")


class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    concept_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("concepts.id", ondelete="CASCADE"), index=True, nullable=False
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    choices: Mapped[list[str] | None] = mapped_column(JSON)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty: Mapped[int] = mapped_column(Integer, nullable=False)
    source_chunk_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime]


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("quiz_questions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    submitted_answer: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    mastery_before: Mapped[float] = mapped_column(Float, nullable=False)
    mastery_after: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime]
