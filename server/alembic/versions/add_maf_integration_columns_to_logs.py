"""add maf integration columns to logs

Revision ID: f9a4e7b2c1d5
Revises: cbb4906847c4
Create Date: 2025-10-25 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f9a4e7b2c1d5'
down_revision: Union[str, None] = 'cbb4906847c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add MAF integration columns to logs table"""
    
    # Add new columns for MAF integration
    op.add_column('logs', sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('logs', sa.Column('session_id', sa.String(length=255), nullable=True))
    op.add_column('logs', sa.Column('agent_id', sa.String(length=255), nullable=True))
    op.add_column('logs', sa.Column('conversation_id', sa.String(length=255), nullable=True))
    op.add_column('logs', sa.Column('input_prompt', sa.Text(), nullable=True))
    op.add_column('logs', sa.Column('llm_response', sa.Text(), nullable=True))
    
    # Add foreign key constraint
    op.create_foreign_key(
        'fk_logs_project_id',
        'logs',
        'projects',
        ['project_id'],
        ['id'],
        ondelete='CASCADE'
    )
    
    # Create indexes for faster queries
    op.create_index('ix_logs_project_id', 'logs', ['project_id'])
    op.create_index('ix_logs_session_id', 'logs', ['session_id'])
    op.create_index('ix_logs_conversation_id', 'logs', ['conversation_id'])


def downgrade() -> None:
    """Remove MAF integration columns from logs table"""
    
    # Drop indexes
    op.drop_index('ix_logs_conversation_id', table_name='logs')
    op.drop_index('ix_logs_session_id', table_name='logs')
    op.drop_index('ix_logs_project_id', table_name='logs')
    
    # Drop foreign key
    op.drop_constraint('fk_logs_project_id', 'logs', type_='foreignkey')
    
    # Drop columns
    op.drop_column('logs', 'llm_response')
    op.drop_column('logs', 'input_prompt')
    op.drop_column('logs', 'conversation_id')
    op.drop_column('logs', 'agent_id')
    op.drop_column('logs', 'session_id')
    op.drop_column('logs', 'project_id')
