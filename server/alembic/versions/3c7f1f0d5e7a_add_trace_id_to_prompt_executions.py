"""add trace_id to prompt_executions

Revision ID: 3c7f1f0d5e7a
Revises: f7f2cd6d0a06
Create Date: 2025-10-27 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "3c7f1f0d5e7a"
down_revision: Union[str, Sequence[str], None] = "f7f2cd6d0a06"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add trace_id column and backfill from execution_traces metadata."""
    op.add_column(
        "prompt_executions",
        sa.Column("trace_id", sa.String(length=255), nullable=True),
    )
    op.create_index(
        "ix_prompt_executions_trace_id",
        "prompt_executions",
        ["trace_id"],
        unique=False,
    )

    # Backfill existing rows using execution_traces.metadata->>'execution_id'
    op.execute(
        sa.text(
            """
            UPDATE prompt_executions pe
            SET trace_id = et.trace_id
            FROM execution_traces et
            WHERE pe.trace_id IS NULL
              AND et.metadata ->> 'execution_id' = pe.id::text
            """
        )
    )


def downgrade() -> None:
    """Remove trace_id column and associated index."""
    op.drop_index("ix_prompt_executions_trace_id", table_name="prompt_executions")
    op.drop_column("prompt_executions", "trace_id")
