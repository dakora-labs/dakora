"""add_api_keys_table

Revision ID: 1655bf1f4bfa
Revises: 74d93bf1ffa5
Create Date: 2025-10-23 09:48:53.403820

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1655bf1f4bfa'
down_revision: Union[str, Sequence[str], None] = '74d93bf1ffa5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create api_keys table
    op.create_table(
        'api_keys',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('project_id', sa.UUID(), nullable=False),

        # Key identification
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('key_prefix', sa.String(length=12), nullable=False),
        sa.Column('key_hash', sa.String(length=255), nullable=False),

        # Metadata
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('last_used_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('expires_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('revoked_at', sa.TIMESTAMP(), nullable=True),

        # Foreign keys
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),

        # Primary key
        sa.PrimaryKeyConstraint('id'),

        # Unique constraint for key prefix per project
        sa.UniqueConstraint('project_id', 'key_prefix', name='unique_key_prefix_per_project')
    )

    # Create indexes
    op.create_index('idx_api_keys_user_project', 'api_keys', ['user_id', 'project_id'])
    op.create_index('idx_api_keys_key_hash', 'api_keys', ['key_hash'])
    # Partial index for non-null expires_at
    op.create_index(
        'idx_api_keys_expires_at',
        'api_keys',
        ['expires_at'],
        postgresql_where=sa.text('expires_at IS NOT NULL')
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.drop_index('idx_api_keys_expires_at', table_name='api_keys')
    op.drop_index('idx_api_keys_key_hash', table_name='api_keys')
    op.drop_index('idx_api_keys_user_project', table_name='api_keys')

    # Drop table
    op.drop_table('api_keys')
