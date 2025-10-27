"""migrate to trace-based logging

Revision ID: a1b2c3d4e5f6
Revises: f9a4e7b2c1d5
Create Date: 2025-01-25 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'f9a4e7b2c1d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Migrate from prompt-centric to trace-based logging model.
    
    Changes:
    1. Add trace_id, parent_trace_id columns to logs
    2. Add conversation_history, metadata JSONB columns
    3. Drop conversation_id, input_prompt, llm_response (replaced by conversation_history)
    4. Create template_executions table for many-to-many linkage
    5. Make existing columns nullable for backward compatibility
    """
    
    # Add new trace-based columns
    op.add_column('logs', sa.Column('trace_id', sa.String(length=255), nullable=True))
    op.add_column('logs', sa.Column('parent_trace_id', sa.String(length=255), nullable=True))
    op.add_column('logs', sa.Column('conversation_history', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('logs', sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    
    # Create unique constraint on trace_id (after backfilling)
    # For now, we'll populate trace_id from existing data
    op.execute("""
        UPDATE logs 
        SET trace_id = CONCAT('legacy-', id::text)
        WHERE trace_id IS NULL
    """)
    
    # Now make trace_id NOT NULL and add unique constraint
    op.alter_column('logs', 'trace_id', nullable=False)
    op.create_unique_constraint('uq_logs_trace_id', 'logs', ['trace_id'])
    
    # Create indexes
    op.create_index('ix_logs_trace_id', 'logs', ['trace_id'])
    op.create_index('ix_logs_parent_trace_id', 'logs', ['parent_trace_id'])
    
    # Drop old MAF-specific columns (replaced by conversation_history)
    op.drop_column('logs', 'conversation_id')
    op.drop_column('logs', 'input_prompt')
    op.drop_column('logs', 'llm_response')
    
    # Create template_executions table
    op.create_table(
        'template_executions',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('trace_id', sa.String(length=255), nullable=False),
        sa.Column('prompt_id', sa.String(length=255), nullable=False),
        sa.Column('version', sa.String(length=50), nullable=False),
        sa.Column('inputs_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('position', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['trace_id'], ['logs.trace_id'], ondelete='CASCADE')
    )
    
    # Create indexes on template_executions
    op.create_index('ix_template_executions_trace_id', 'template_executions', ['trace_id'])
    op.create_index('ix_template_executions_prompt_id', 'template_executions', ['prompt_id'])
    
    # Migrate existing prompt-based logs to template_executions
    # This links old logs to their templates
    op.execute("""
        INSERT INTO template_executions (trace_id, prompt_id, version, inputs_json, position)
        SELECT 
            trace_id,
            prompt_id,
            COALESCE(version, '1.0.0') as version,
            CASE 
                WHEN inputs_json IS NOT NULL AND inputs_json != '' 
                THEN inputs_json::jsonb 
                ELSE NULL 
            END as inputs_json,
            0 as position
        FROM logs
        WHERE prompt_id IS NOT NULL
    """)


def downgrade() -> None:
    """
    Revert to prompt-centric logging model.
    
    WARNING: This will lose data stored in conversation_history and metadata columns.
    """
    
    # Drop template_executions table
    op.drop_index('ix_template_executions_prompt_id', table_name='template_executions')
    op.drop_index('ix_template_executions_trace_id', table_name='template_executions')
    op.drop_table('template_executions')
    
    # Re-add old columns
    op.add_column('logs', sa.Column('conversation_id', sa.String(length=255), nullable=True))
    op.add_column('logs', sa.Column('input_prompt', sa.Text(), nullable=True))
    op.add_column('logs', sa.Column('llm_response', sa.Text(), nullable=True))
    
    # Recreate index
    op.create_index('ix_logs_conversation_id', 'logs', ['conversation_id'])
    
    # Drop new columns
    op.drop_index('ix_logs_parent_trace_id', table_name='logs')
    op.drop_index('ix_logs_trace_id', table_name='logs')
    op.drop_constraint('uq_logs_trace_id', 'logs', type_='unique')
    op.drop_column('logs', 'metadata')
    op.drop_column('logs', 'conversation_history')
    op.drop_column('logs', 'parent_trace_id')
    op.drop_column('logs', 'trace_id')
