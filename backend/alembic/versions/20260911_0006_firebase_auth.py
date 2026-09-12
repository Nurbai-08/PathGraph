"""Add Firebase identities to users.

Revision ID: 20260911_0006
Revises: 20260911_0005
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260911_0006"
down_revision: str | None = "20260911_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("firebase_uid", sa.String(length=128), nullable=True))
        batch_op.alter_column(
            "password_hash",
            existing_type=sa.String(length=255),
            nullable=True,
        )
        batch_op.create_index("ix_users_firebase_uid", ["firebase_uid"], unique=True)


def downgrade() -> None:
    op.execute(
        sa.text("UPDATE users SET password_hash = '!firebase-only' WHERE password_hash IS NULL")
    )
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_index("ix_users_firebase_uid")
        batch_op.alter_column(
            "password_hash",
            existing_type=sa.String(length=255),
            nullable=False,
        )
        batch_op.drop_column("firebase_uid")
