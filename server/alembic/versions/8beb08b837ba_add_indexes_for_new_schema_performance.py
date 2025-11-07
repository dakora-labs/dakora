"""add_indexes_for_new_schema_performance

Revision ID: 8beb08b837ba
Revises: bd52ef259a6f
Create Date: 2025-11-04 13:07:43.409593

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8beb08b837ba'
down_revision: Union[str, Sequence[str], None] = 'bd52ef259a6f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Index for list query filtering and sorting on executions table
    # Covers: project_id, type, start_time for the main aggregation query
    op.create_index(
        'idx_executions_project_type_time',
        'executions',
        ['project_id', 'type', sa.text('start_time DESC')],
        unique=False,
        postgresql_ops={'start_time': 'DESC'}
    )
    
    # Index for parent-child span relationships
    # Covers: trace_id, parent_span_id, type for hierarchical queries
    op.create_index(
        'idx_executions_trace_parent_type',
        'executions',
        ['trace_id', 'parent_span_id', 'type'],
        unique=False
    )
    
    # Index for agent filtering (used in list queries)
    # Covers: agent_name for agent-specific filtering
    op.create_index(
        'idx_executions_agent_name',
        'executions',
        ['agent_name'],
        unique=False,
        postgresql_where=sa.text('agent_name IS NOT NULL')
    )
    
    # Index for template_traces lookups by trace_id
    # Already exists based on schema but ensuring it's optimized
    # This is critical for the post-pagination template counting
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_template_traces_trace_id 
        ON template_traces(trace_id)
        """
    )
    
    # Index for cost-based filtering
    # Covers: total_cost_usd for min_cost filter
    op.create_index(
        'idx_executions_cost',
        'executions',
        ['total_cost_usd'],
        unique=False,
        postgresql_where=sa.text('total_cost_usd IS NOT NULL')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_executions_cost', table_name='executions')
    op.execute('DROP INDEX IF EXISTS idx_template_traces_trace_id')
    op.drop_index('idx_executions_agent_name', table_name='executions')
    op.drop_index('idx_executions_trace_parent_type', table_name='executions')
    op.drop_index('idx_executions_project_type_time', table_name='executions')
