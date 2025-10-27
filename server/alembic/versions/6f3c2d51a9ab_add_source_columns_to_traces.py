"""add source columns to execution and template traces

Revision ID: 6f3c2d51a9ab
Revises: 3c7f1f0d5e7a
Create Date: 2025-10-27 02:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "6f3c2d51a9ab"
down_revision: Union[str, None] = "3c7f1f0d5e7a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "execution_traces",
        sa.Column("source", sa.String(length=50), nullable=True),
    )
    op.create_index(
        op.f("ix_execution_traces_source"),
        "execution_traces",
        ["source"],
        unique=False,
    )

    op.add_column(
        "template_traces",
        sa.Column("role", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "template_traces",
        sa.Column("source", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "template_traces",
        sa.Column("message_index", sa.Integer(), nullable=True),
    )
    op.add_column(
        "template_traces",
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("template_traces", "metadata_json")
    op.drop_column("template_traces", "message_index")
    op.drop_column("template_traces", "source")
    op.drop_column("template_traces", "role")

    op.drop_index(op.f("ix_execution_traces_source"), table_name="execution_traces")
    op.drop_column("execution_traces", "source")
