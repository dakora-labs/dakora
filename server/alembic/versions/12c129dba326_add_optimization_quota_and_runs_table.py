"""add optimization quota and runs table

Revision ID: 12c129dba326
Revises: 4c2252bbbbd9
Create Date: 2025-10-25 21:28:09.183651

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '12c129dba326'
down_revision: Union[str, Sequence[str], None] = '4c2252bbbbd9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add optimization quota columns to workspace_quotas table
    op.add_column('workspace_quotas', sa.Column('optimization_runs_used_month', sa.Integer(), server_default='0', nullable=False))

    # Create optimization_runs table
    op.create_table(
        'optimization_runs',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('project_id', sa.UUID(), nullable=False),
        sa.Column('prompt_id', sa.String(length=255), nullable=False),
        sa.Column('version', sa.String(length=50), nullable=False),
        sa.Column('original_template', sa.Text(), nullable=False),
        sa.Column('optimized_template', sa.Text(), nullable=False),
        sa.Column('insights', sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column('token_reduction_pct', sa.Float(), nullable=True),
        sa.Column('applied', sa.Integer(), server_default='0', nullable=False),
        sa.Column('user_id', sa.String(length=255), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Add indexes for efficient queries
    op.create_index('ix_optimization_runs_project_id', 'optimization_runs', ['project_id'])
    op.create_index('ix_optimization_runs_prompt_id', 'optimization_runs', ['prompt_id'])
    op.create_index('ix_optimization_runs_created_at', 'optimization_runs', ['created_at'])
    op.create_index('ix_optimization_runs_workspace_id', 'optimization_runs', ['workspace_id'])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.drop_index('ix_optimization_runs_workspace_id', table_name='optimization_runs')
    op.drop_index('ix_optimization_runs_created_at', table_name='optimization_runs')
    op.drop_index('ix_optimization_runs_prompt_id', table_name='optimization_runs')
    op.drop_index('ix_optimization_runs_project_id', table_name='optimization_runs')

    # Drop table
    op.drop_table('optimization_runs')

    # Remove column
    op.drop_column('workspace_quotas', 'optimization_runs_used_month')
