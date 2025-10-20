"""Initial migration - logs table

Revision ID: 8f97975fec5c
Revises: 
Create Date: 2025-10-20 19:40:19.847199

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8f97975fec5c'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create logs table for execution logging."""
    op.create_table(
        'logs',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('prompt_id', sa.String(length=255), nullable=True),
        sa.Column('version', sa.String(length=50), nullable=True),
        sa.Column('inputs_json', sa.Text(), nullable=True),
        sa.Column('output_text', sa.Text(), nullable=True),
        sa.Column('cost', sa.Float(), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('provider', sa.String(length=50), nullable=True),
        sa.Column('model', sa.String(length=100), nullable=True),
        sa.Column('tokens_in', sa.Integer(), nullable=True),
        sa.Column('tokens_out', sa.Integer(), nullable=True),
        sa.Column('cost_usd', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for common queries
    op.create_index('ix_logs_prompt_id', 'logs', ['prompt_id'])
    op.create_index('ix_logs_created_at', 'logs', ['created_at'])
    op.create_index('ix_logs_model', 'logs', ['model'])


def downgrade() -> None:
    """Drop logs table."""
    op.drop_index('ix_logs_model', table_name='logs')
    op.drop_index('ix_logs_created_at', table_name='logs')
    op.drop_index('ix_logs_prompt_id', table_name='logs')
    op.drop_table('logs')
