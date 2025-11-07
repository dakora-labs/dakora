"""add_otlp_constraints_and_indexes

Revision ID: 731bc24c7cfa
Revises: 7e9e79caa0dd
Create Date: 2025-10-31 12:54:42.288977

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '731bc24c7cfa'
down_revision: Union[str, Sequence[str], None] = '7e9e79caa0dd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add unique constraint on span_id to prevent duplicate span storage
    op.create_unique_constraint(
        'uq_otel_spans_span_id',
        'otel_spans',
        ['span_id']
    )

    # Add index on parent_span_id for efficient child span lookups
    op.create_index(
        'idx_otel_spans_parent_span_id',
        'otel_spans',
        ['parent_span_id']
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop index first (dependent on table)
    op.drop_index('idx_otel_spans_parent_span_id', table_name='otel_spans')

    # Drop unique constraint
    op.drop_constraint('uq_otel_spans_span_id', 'otel_spans', type_='unique')
