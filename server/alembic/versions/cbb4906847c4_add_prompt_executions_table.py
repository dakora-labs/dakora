"""add_prompt_executions_table

Revision ID: cbb4906847c4
Revises: 1231c8dc0405
Create Date: 2025-10-24 14:10:27.918311

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cbb4906847c4'
down_revision: Union[str, Sequence[str], None] = '1231c8dc0405'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'prompt_executions',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('project_id', sa.UUID(), nullable=False),
        sa.Column('prompt_id', sa.String(255), nullable=False),
        sa.Column('version', sa.String(50), nullable=False),

        # Execution details
        sa.Column('inputs_json', sa.JSON(), nullable=False),
        sa.Column('model', sa.String(100), nullable=False),
        sa.Column('provider', sa.String(50), nullable=False),

        # Results
        sa.Column('output_text', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False),

        # Metrics
        sa.Column('tokens_input', sa.Integer(), nullable=True),
        sa.Column('tokens_output', sa.Integer(), nullable=True),
        sa.Column('tokens_total', sa.Integer(), nullable=True),
        sa.Column('cost_usd', sa.Numeric(10, 6), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=True),

        # Metadata
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('NOW()')),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE')
    )

    # Indexes for fast queries
    op.create_index(
        'idx_executions_prompt',
        'prompt_executions',
        ['project_id', 'prompt_id', sa.text('created_at DESC')]
    )
    op.create_index(
        'idx_executions_workspace',
        'prompt_executions',
        ['workspace_id', sa.text('created_at DESC')]
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_executions_workspace', table_name='prompt_executions')
    op.drop_index('idx_executions_prompt', table_name='prompt_executions')
    op.drop_table('prompt_executions')
