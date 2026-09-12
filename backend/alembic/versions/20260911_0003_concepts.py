"""Add AI settings and concepts.

Revision ID: 20260911_0003
Revises: 20260911_0002
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260911_0003"
down_revision: str | None = "20260911_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_settings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=16), nullable=False),
        sa.Column("base_url", sa.String(length=500), nullable=True),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("embedding_model", sa.String(length=120), nullable=False),
        sa.Column("api_key_encrypted", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_table(
        "concepts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("normalized_name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("type", sa.String(length=80), nullable=False),
        sa.Column("importance", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("embedding", sa.JSON(), nullable=True),
        sa.Column("is_manual", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "normalized_name", name="uq_concepts_normalized_name"),
    )
    op.create_index(op.f("ix_concepts_workspace_id"), "concepts", ["workspace_id"])
    op.create_table(
        "ai_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=True),
        sa.Column("provider", sa.String(length=16), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("operation", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["job_id"], ["processing_jobs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ai_runs_job_id"), "ai_runs", ["job_id"])
    op.create_table(
        "concept_aliases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("concept_id", sa.Uuid(), nullable=False),
        sa.Column("alias", sa.String(length=200), nullable=False),
        sa.Column("normalized_alias", sa.String(length=200), nullable=False),
        sa.ForeignKeyConstraint(["concept_id"], ["concepts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("concept_id", "normalized_alias", name="uq_concept_aliases_normalized"),
    )
    op.create_index(op.f("ix_concept_aliases_concept_id"), "concept_aliases", ["concept_id"])
    op.create_table(
        "concept_edges",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("source_concept_id", sa.Uuid(), nullable=False),
        sa.Column("target_concept_id", sa.Uuid(), nullable=False),
        sa.Column("relation_type", sa.String(length=40), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["source_concept_id"], ["concepts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_concept_id"], ["concepts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workspace_id",
            "source_concept_id",
            "target_concept_id",
            "relation_type",
            name="uq_concept_edges_relation",
        ),
    )
    op.create_index(op.f("ix_concept_edges_workspace_id"), "concept_edges", ["workspace_id"])
    op.create_index(
        op.f("ix_concept_edges_source_concept_id"), "concept_edges", ["source_concept_id"]
    )
    op.create_index(
        op.f("ix_concept_edges_target_concept_id"), "concept_edges", ["target_concept_id"]
    )
    op.create_table(
        "concept_sources",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("concept_id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_id", sa.Uuid(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["chunk_id"], ["chunks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["concept_id"], ["concepts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "concept_id", "source_id", "chunk_id", name="uq_concept_source_evidence"
        ),
    )
    op.create_index(op.f("ix_concept_sources_chunk_id"), "concept_sources", ["chunk_id"])
    op.create_index(op.f("ix_concept_sources_concept_id"), "concept_sources", ["concept_id"])
    op.create_index(op.f("ix_concept_sources_source_id"), "concept_sources", ["source_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_concept_sources_source_id"), table_name="concept_sources")
    op.drop_index(op.f("ix_concept_sources_concept_id"), table_name="concept_sources")
    op.drop_index(op.f("ix_concept_sources_chunk_id"), table_name="concept_sources")
    op.drop_table("concept_sources")
    op.drop_index(op.f("ix_concept_edges_target_concept_id"), table_name="concept_edges")
    op.drop_index(op.f("ix_concept_edges_source_concept_id"), table_name="concept_edges")
    op.drop_index(op.f("ix_concept_edges_workspace_id"), table_name="concept_edges")
    op.drop_table("concept_edges")
    op.drop_index(op.f("ix_concept_aliases_concept_id"), table_name="concept_aliases")
    op.drop_table("concept_aliases")
    op.drop_index(op.f("ix_ai_runs_job_id"), table_name="ai_runs")
    op.drop_table("ai_runs")
    op.drop_index(op.f("ix_concepts_workspace_id"), table_name="concepts")
    op.drop_table("concepts")
    op.drop_table("ai_settings")
