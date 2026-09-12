"""Add chunk embeddings for retrieval.

Revision ID: 20260911_0005
Revises: 20260911_0004
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260911_0005"
down_revision: str | None = "20260911_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("chunks", sa.Column("embedding", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("chunks", "embedding")
