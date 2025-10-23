"""Add key_suffix column to api_keys

Revision ID: 80ca7cf8295a
Revises: 1655bf1f4bfa
Create Date: 2025-10-23 11:31:00.484817

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '80ca7cf8295a'
down_revision: Union[str, Sequence[str], None] = '1655bf1f4bfa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add key_suffix column
    op.add_column('api_keys', sa.Column('key_suffix', sa.String(4), nullable=True))

    # Migrate existing data: use placeholder since we don't have the original full key
    op.execute("UPDATE api_keys SET key_suffix = 'xxxx' WHERE key_suffix IS NULL")

    # Truncate existing key_prefix values from 12 to 8 chars
    op.execute("UPDATE api_keys SET key_prefix = SUBSTRING(key_prefix FROM 1 FOR 8)")

    # Make key_suffix non-nullable
    op.alter_column('api_keys', 'key_suffix', nullable=False)

    # Alter key_prefix to 8 chars (from 12)
    op.alter_column('api_keys', 'key_prefix', type_=sa.String(8))


def downgrade() -> None:
    """Downgrade schema."""
    # Revert key_prefix to 12 chars
    op.alter_column('api_keys', 'key_prefix', type_=sa.String(12))

    # Drop key_suffix column
    op.drop_column('api_keys', 'key_suffix')
