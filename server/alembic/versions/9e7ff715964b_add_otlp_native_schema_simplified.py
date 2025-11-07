"""add_otlp_native_schema_simplified

Creates OTLP-native schema for proper span hierarchy and observability.

New tables:
- traces: Trace-level metadata
- executions: Individual spans with hierarchy support
- execution_messages: Normalized conversation messages
- tool_invocations: Tool/function call tracking

Updates:
- template_traces: Add span_id FK to link to specific spans

Revision ID: 9e7ff715964b
Revises: 731bc24c7cfa
Create Date: 2025-11-03 14:14:55.895343

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision: str = '9e7ff715964b'
down_revision: Union[str, Sequence[str], None] = '731bc24c7cfa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create OTLP-native schema tables."""
    
    # ========== TABLE 1: traces ==========
    # Trace-level metadata (one row per trace_id)
    op.create_table(
        'traces',
        sa.Column('trace_id', sa.Text(), nullable=False),
        sa.Column('project_id', UUID(as_uuid=True), nullable=False),
        sa.Column('provider', sa.Text(), nullable=True),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('duration_ms', sa.Integer(), 
                  sa.Computed('(EXTRACT(EPOCH FROM (end_time - start_time))*1000)::INT', persisted=True)),
        sa.Column('attributes', JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), 
                  server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], 
                                ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('trace_id'),
        comment='Trace-level metadata grouping multiple spans'
    )
    
    op.create_index('idx_traces_project_time', 'traces', 
                    ['project_id', sa.text('start_time DESC')])
    op.create_index('idx_traces_provider', 'traces', ['provider'], 
                    postgresql_where=sa.text('provider IS NOT NULL'))
    
    # ========== TABLE 2: executions ==========
    # Individual spans with hierarchy (one row per span)
    op.create_table(
        'executions',
        sa.Column('trace_id', sa.Text(), nullable=False),
        sa.Column('span_id', sa.Text(), nullable=False),
        sa.Column('parent_span_id', sa.Text(), nullable=True),
        sa.Column('type', sa.Text(), nullable=False),
        sa.Column('span_kind', sa.Text(), nullable=True),
        sa.Column('agent_id', sa.Text(), nullable=True),
        sa.Column('agent_name', sa.Text(), nullable=True),
        sa.Column('provider', sa.Text(), nullable=True),
        sa.Column('model', sa.Text(), nullable=True),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('latency_ms', sa.Integer(),
                  sa.Computed('(EXTRACT(EPOCH FROM (end_time - start_time))*1000)::INT', persisted=True)),
        sa.Column('tokens_in', sa.Integer(), nullable=True),
        sa.Column('tokens_out', sa.Integer(), nullable=True),
        sa.Column('input_cost_usd', sa.Numeric(20, 8), nullable=True),
        sa.Column('output_cost_usd', sa.Numeric(20, 8), nullable=True),
        sa.Column('total_cost_usd', sa.Numeric(20, 8), nullable=True),
        sa.Column('status', sa.Text(), nullable=True),
        sa.Column('status_message', sa.Text(), nullable=True),
        sa.Column('attributes', JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('NOW()'), nullable=False),
        sa.CheckConstraint(
            "type IN ('agent', 'chat', 'tool', 'llm', 'message_send', "
            "'executor_process', 'edge_group_process', 'workflow_run', 'workflow_build')",
            name='chk_execution_type'
        ),
        sa.CheckConstraint(
            "span_kind IN ('INTERNAL', 'CLIENT', 'SERVER', 'PRODUCER', 'CONSUMER')",
            name='chk_span_kind'
        ),
        sa.CheckConstraint(
            "status IN ('UNSET', 'OK', 'ERROR')",
            name='chk_status'
        ),
        sa.CheckConstraint(
            'span_id IS DISTINCT FROM parent_span_id',
            name='chk_no_cycle'
        ),
        sa.ForeignKeyConstraint(['trace_id'], ['traces.trace_id'], 
                                ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('trace_id', 'span_id'),
        comment='Individual spans within a trace (supports hierarchy)'
    )
    
    # Add self-referential FK AFTER table creation (with DEFERRABLE)
    op.execute("""
        ALTER TABLE executions
        ADD CONSTRAINT fk_exec_parent
        FOREIGN KEY (trace_id, parent_span_id)
        REFERENCES executions(trace_id, span_id)
        DEFERRABLE INITIALLY DEFERRED
    """)
    
    # Indexes for executions
    op.create_index('idx_execs_trace_parent', 'executions', 
                    ['trace_id', 'parent_span_id'])
    op.create_index('idx_execs_time', 'executions', 
                    [sa.text('start_time DESC')])
    op.create_index('idx_execs_type_time', 'executions', 
                    ['type', sa.text('start_time DESC')])
    op.create_index('idx_execs_provider_model', 'executions', 
                    ['provider', 'model'],
                    postgresql_where=sa.text('provider IS NOT NULL AND model IS NOT NULL'))
    op.create_index('idx_execs_root_spans', 'executions', ['trace_id'],
                    postgresql_where=sa.text('parent_span_id IS NULL'))
    
    # ========== TABLE 3: execution_messages ==========
    # Normalized conversation messages
    op.create_table(
        'execution_messages',
        sa.Column('id', UUID(as_uuid=True), 
                  server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('trace_id', sa.Text(), nullable=False),
        sa.Column('span_id', sa.Text(), nullable=False),
        sa.Column('direction', sa.Text(), nullable=False),
        sa.Column('msg_index', sa.Integer(), nullable=False),
        sa.Column('role', sa.Text(), nullable=False),
        sa.Column('parts', JSONB(), nullable=False),
        sa.Column('finish_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('NOW()'), nullable=False),
        sa.CheckConstraint(
            "direction IN ('input', 'output')",
            name='chk_message_direction'
        ),
        sa.CheckConstraint(
            "role IN ('system', 'user', 'assistant', 'tool')",
            name='chk_message_role'
        ),
        sa.ForeignKeyConstraint(['trace_id', 'span_id'], 
                                ['executions.trace_id', 'executions.span_id'],
                                ondelete='CASCADE', name='fk_exec_msgs'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('trace_id', 'span_id', 'direction', 'msg_index',
                           name='ux_exec_msgs_order'),
        comment='Individual messages within an execution'
    )
    
    # Add tsvector column for full-text search
    op.execute("""
        ALTER TABLE execution_messages
        ADD COLUMN message_text_tsv tsvector
        GENERATED ALWAYS AS (to_tsvector('english', parts::text)) STORED
    """)
    
    # Indexes for messages (but skip GIN indexes for now - add later)
    op.create_index('idx_exec_msgs_execution', 'execution_messages',
                    ['trace_id', 'span_id'])
    op.create_index('idx_exec_msgs_role', 'execution_messages', ['role'])
    
    # ========== TABLE 4: tool_invocations ==========
    # Tool/function call tracking
    op.create_table(
        'tool_invocations',
        sa.Column('id', UUID(as_uuid=True),
                  server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('trace_id', sa.Text(), nullable=False),
        sa.Column('span_id', sa.Text(), nullable=False),
        sa.Column('tool_call_id', sa.Text(), nullable=False),
        sa.Column('tool_name', sa.Text(), nullable=False),
        sa.Column('arguments', JSONB(), nullable=True),
        sa.Column('result', JSONB(), nullable=True),
        sa.Column('status', sa.Text(), nullable=False),
        sa.Column('error_type', sa.Text(), nullable=True),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('latency_ms', sa.Integer(),
                  sa.Computed(
                      'CASE WHEN start_time IS NOT NULL AND end_time IS NOT NULL '
                      'THEN (EXTRACT(EPOCH FROM (end_time - start_time))*1000)::INT '
                      'ELSE NULL END'
                  , persisted=True)),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('NOW()'), nullable=False),
        sa.CheckConstraint(
            "status IN ('ok', 'error')",
            name='chk_tool_status'
        ),
        sa.ForeignKeyConstraint(['trace_id', 'span_id'],
                                ['executions.trace_id', 'executions.span_id'],
                                ondelete='CASCADE', name='fk_tool_exec'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('trace_id', 'tool_call_id',
                           name='ux_tool_invocations_call'),
        comment='Tool/function calls within executions'
    )
    
    op.create_index('idx_tool_invocations_exec', 'tool_invocations',
                    ['trace_id', 'span_id'])
    op.create_index('idx_tool_invocations_name', 'tool_invocations',
                    ['tool_name'])
    op.create_index('idx_tool_invocations_status', 'tool_invocations',
                    ['status', sa.text('created_at DESC')])
    
    # ========== UPDATE: template_traces ==========
    # Add span_id to link templates to specific spans
    op.add_column('template_traces',
                  sa.Column('span_id', sa.Text(), nullable=True))
    
    # Note: span_id will be populated during data migration
    # After migration, we'll make it NOT NULL and add FK constraint


def downgrade() -> None:
    """Revert schema changes."""
    # Drop in reverse order (respecting FK constraints)
    op.drop_column('template_traces', 'span_id')
    op.drop_table('tool_invocations')
    op.drop_table('execution_messages')
    op.drop_table('executions')
    op.drop_table('traces')
