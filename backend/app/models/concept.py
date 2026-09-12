import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.source import Chunk, Source
    from app.models.workspace import Workspace


class Concept(TimestampMixin, Base):
    __tablename__ = "concepts"
    __table_args__ = (
        UniqueConstraint("workspace_id", "normalized_name", name="uq_concepts_normalized_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("workspaces.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    type: Mapped[str] = mapped_column(String(80), default="concept", nullable=False)
    importance: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(JSON)
    is_manual: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    workspace: Mapped["Workspace"] = relationship(back_populates="concepts")
    aliases: Mapped[list["ConceptAlias"]] = relationship(
        back_populates="concept", cascade="all, delete-orphan"
    )
    evidence: Mapped[list["ConceptSource"]] = relationship(
        back_populates="concept", cascade="all, delete-orphan"
    )


class ConceptAlias(Base):
    __tablename__ = "concept_aliases"
    __table_args__ = (
        UniqueConstraint("concept_id", "normalized_alias", name="uq_concept_aliases_normalized"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    concept_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("concepts.id", ondelete="CASCADE"), index=True, nullable=False
    )
    alias: Mapped[str] = mapped_column(String(200), nullable=False)
    normalized_alias: Mapped[str] = mapped_column(String(200), nullable=False)

    concept: Mapped[Concept] = relationship(back_populates="aliases")


class ConceptSource(Base):
    __tablename__ = "concept_sources"
    __table_args__ = (
        UniqueConstraint("concept_id", "source_id", "chunk_id", name="uq_concept_source_evidence"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    concept_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("concepts.id", ondelete="CASCADE"), index=True, nullable=False
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("sources.id", ondelete="CASCADE"), index=True, nullable=False
    )
    chunk_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("chunks.id", ondelete="CASCADE"), index=True, nullable=False
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    concept: Mapped[Concept] = relationship(back_populates="evidence")
    source: Mapped["Source"] = relationship(back_populates="concept_evidence")
    chunk: Mapped["Chunk"] = relationship(back_populates="concept_evidence")


class ConceptEdge(Base):
    __tablename__ = "concept_edges"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "source_concept_id",
            "target_concept_id",
            "relation_type",
            name="uq_concept_edges_relation",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("workspaces.id", ondelete="CASCADE"), index=True, nullable=False
    )
    source_concept_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("concepts.id", ondelete="CASCADE"), index=True, nullable=False
    )
    target_concept_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("concepts.id", ondelete="CASCADE"), index=True, nullable=False
    )
    relation_type: Mapped[str] = mapped_column(String(40), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
