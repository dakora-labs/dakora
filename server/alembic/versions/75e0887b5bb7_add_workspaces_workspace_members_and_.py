"""Add workspaces, workspace_members, and projects tables

Revision ID: 75e0887b5bb7
Revises: e533777ef92c
Create Date: 2025-10-22 09:51:39.462476

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '75e0887b5bb7'
down_revision: Union[str, Sequence[str], None] = 'e533777ef92c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create workspaces table
    op.create_table(
        'workspaces',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('slug', sa.String(length=63), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('type', sa.String(length=20), nullable=False),
        sa.Column('owner_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug')
    )
    op.create_index('idx_workspaces_slug', 'workspaces', ['slug'])
    op.create_index('idx_workspaces_owner', 'workspaces', ['owner_id'])

    # Create workspace_members table
    op.create_table(
        'workspace_members',
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('joined_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('workspace_id', 'user_id')
    )
    op.create_index('idx_members_user', 'workspace_members', ['user_id'])

    # Create projects table
    op.create_table(
        'projects',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('slug', sa.String(length=63), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('workspace_id', 'slug', name='uq_projects_workspace_slug')
    )
    op.create_index('idx_projects_workspace', 'projects', ['workspace_id'])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop tables in reverse order (respecting foreign key constraints)
    op.drop_index('idx_projects_workspace', table_name='projects')
    op.drop_table('projects')

    op.drop_index('idx_members_user', table_name='workspace_members')
    op.drop_table('workspace_members')

    op.drop_index('idx_workspaces_owner', table_name='workspaces')
    op.drop_index('idx_workspaces_slug', table_name='workspaces')
    op.drop_table('workspaces')
