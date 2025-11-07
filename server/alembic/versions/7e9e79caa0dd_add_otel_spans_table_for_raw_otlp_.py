"""add otel_spans table for raw OTLP storage

Revision ID: 7e9e79caa0dd
Revises: a6126327dd28
Create Date: 2025-10-31 09:11:19.989027

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID


# revision identifiers, used by Alembic.
revision: str = '7e9e79caa0dd'
down_revision: Union[str, Sequence[str], None] = 'a6126327dd28'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'otel_spans',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        # OTLP identifiers
        sa.Column('trace_id', sa.String(32), nullable=False, index=True),
        sa.Column('span_id', sa.String(16), nullable=False, unique=True, index=True),
        sa.Column('parent_span_id', sa.String(16), nullable=True, index=True),
        # Project context
        sa.Column('project_id', UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=True, index=True),
        # Span metadata
        sa.Column('span_name', sa.String(255), nullable=False),
        sa.Column('span_kind', sa.String(50), nullable=True),
        # OTLP data (raw storage)
        sa.Column('attributes', JSONB, nullable=True),
        sa.Column('events', JSONB, nullable=True),
        # Timing
        sa.Column('start_time_ns', sa.BigInteger(), nullable=False),
        sa.Column('end_time_ns', sa.BigInteger(), nullable=False),
        sa.Column('duration_ns', sa.BigInteger(), nullable=False),
        # Status
        sa.Column('status_code', sa.String(20), nullable=True),
        sa.Column('status_message', sa.String(255), nullable=True),
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text("(NOW() AT TIME ZONE 'UTC')"), nullable=False),
    )

    # Composite index for trace queries
    op.create_index('idx_otel_spans_trace_project', 'otel_spans', ['trace_id', 'project_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_otel_spans_trace_project', table_name='otel_spans')
    op.drop_table('otel_spans')
