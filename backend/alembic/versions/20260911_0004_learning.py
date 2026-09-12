"""Add learning paths, knowledge states, and quizzes.

Revision ID: 20260911_0004
Revises: 20260911_0003
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260911_0004"
down_revision: str | None = "20260911_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "knowledge_states",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("concept_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("mastery", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("last_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["concept_id"], ["concepts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "concept_id", name="uq_knowledge_state_user_concept"),
    )
    op.create_index(op.f("ix_knowledge_states_concept_id"), "knowledge_states", ["concept_id"])
    op.create_index(op.f("ix_knowledge_states_user_id"), "knowledge_states", ["user_id"])
    op.create_table(
        "learning_paths",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_learning_paths_workspace_id"), "learning_paths", ["workspace_id"])
    op.create_table(
        "quiz_questions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("concept_id", sa.Uuid(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("choices", sa.JSON(), nullable=True),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("difficulty", sa.Integer(), nullable=False),
        sa.Column("source_chunk_ids", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["concept_id"], ["concepts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_quiz_questions_concept_id"), "quiz_questions", ["concept_id"])
    op.create_table(
        "learning_path_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("learning_path_id", sa.Uuid(), nullable=False),
        sa.Column("concept_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.ForeignKeyConstraint(["concept_id"], ["concepts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["learning_path_id"], ["learning_paths.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("learning_path_id", "concept_id", name="uq_learning_path_concept"),
        sa.UniqueConstraint("learning_path_id", "position", name="uq_learning_path_position"),
    )
    op.create_index(
        op.f("ix_learning_path_items_concept_id"), "learning_path_items", ["concept_id"]
    )
    op.create_index(
        op.f("ix_learning_path_items_learning_path_id"),
        "learning_path_items",
        ["learning_path_id"],
    )
    op.create_table(
        "quiz_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("question_id", sa.Uuid(), nullable=False),
        sa.Column("submitted_answer", sa.Text(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("mastery_before", sa.Float(), nullable=False),
        sa.Column("mastery_after", sa.Float(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["question_id"], ["quiz_questions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_quiz_attempts_question_id"), "quiz_attempts", ["question_id"])
    op.create_index(op.f("ix_quiz_attempts_user_id"), "quiz_attempts", ["user_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_quiz_attempts_user_id"), table_name="quiz_attempts")
    op.drop_index(op.f("ix_quiz_attempts_question_id"), table_name="quiz_attempts")
    op.drop_table("quiz_attempts")
    op.drop_index(op.f("ix_learning_path_items_learning_path_id"), table_name="learning_path_items")
    op.drop_index(op.f("ix_learning_path_items_concept_id"), table_name="learning_path_items")
    op.drop_table("learning_path_items")
    op.drop_index(op.f("ix_quiz_questions_concept_id"), table_name="quiz_questions")
    op.drop_table("quiz_questions")
    op.drop_index(op.f("ix_learning_paths_workspace_id"), table_name="learning_paths")
    op.drop_table("learning_paths")
    op.drop_index(op.f("ix_knowledge_states_user_id"), table_name="knowledge_states")
    op.drop_index(op.f("ix_knowledge_states_concept_id"), table_name="knowledge_states")
    op.drop_table("knowledge_states")
