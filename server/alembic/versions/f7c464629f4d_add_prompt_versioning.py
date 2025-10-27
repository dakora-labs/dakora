"""add_prompt_versioning

Revision ID: f7c464629f4d
Revises: 12c129dba326
Create Date: 2025-10-26 18:48:18.328634

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f7c464629f4d'
down_revision: Union[str, Sequence[str], None] = '12c129dba326'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add version tracking columns to prompts table
    op.add_column('prompts', sa.Column('version_number', sa.Integer(), server_default='1', nullable=False))
    op.add_column('prompts', sa.Column('content_hash', sa.String(length=64), nullable=True))

    # Create prompt_versions table
    op.create_table(
        'prompt_versions',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('prompt_id', sa.UUID(), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('storage_path', sa.Text(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.ForeignKeyConstraint(['prompt_id'], ['prompts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # Add unique constraint and indexes
    op.create_unique_constraint('uq_prompt_versions_prompt_id_version_number', 'prompt_versions', ['prompt_id', 'version_number'])
    op.create_index('ix_prompt_versions_prompt_id', 'prompt_versions', ['prompt_id'])
    op.create_index('ix_prompt_versions_created_at', 'prompt_versions', ['created_at'])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes and constraints
    op.drop_index('ix_prompt_versions_created_at', table_name='prompt_versions')
    op.drop_index('ix_prompt_versions_prompt_id', table_name='prompt_versions')
    op.drop_constraint('uq_prompt_versions_prompt_id_version_number', 'prompt_versions', type_='unique')

    # Drop table
    op.drop_table('prompt_versions')

    # Remove columns from prompts table
    op.drop_column('prompts', 'content_hash')
    op.drop_column('prompts', 'version_number')