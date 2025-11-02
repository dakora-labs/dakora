"""add_user_feedback_table

Revision ID: ecbcf45f7a59
Revises: a6126327dd28
Create Date: 2025-11-02 12:33:26.377104

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = 'ecbcf45f7a59'
down_revision: Union[str, Sequence[str], None] = 'a6126327dd28'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create user_feedback table."""
    op.create_table(
        'user_feedback',
        sa.Column('id', sa.UUID(), nullable=False, server_default=text("gen_random_uuid()")),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('project_id', sa.UUID(), nullable=True),
        sa.Column('workspace_id', sa.UUID(), nullable=True),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('feedback', sa.Text(), nullable=True),
        sa.Column('user_email', sa.String(255), nullable=True),
        sa.Column('user_name', sa.String(255), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=text("(NOW() AT TIME ZONE 'UTC')"), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
    )
    op.create_index('idx_user_feedback_user_id', 'user_feedback', ['user_id'])
    op.create_index('idx_user_feedback_project_id', 'user_feedback', ['project_id'])
    op.create_index('idx_user_feedback_workspace_id', 'user_feedback', ['workspace_id'])
    op.create_index('idx_user_feedback_created_at', 'user_feedback', ['created_at'])


def downgrade() -> None:
    """Drop user_feedback table."""
    op.drop_index('idx_user_feedback_created_at', table_name='user_feedback')
    op.drop_index('idx_user_feedback_workspace_id', table_name='user_feedback')
    op.drop_index('idx_user_feedback_project_id', table_name='user_feedback')
    op.drop_index('idx_user_feedback_user_id', table_name='user_feedback')
    op.drop_table('user_feedback')
