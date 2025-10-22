"""Add users table

Revision ID: e533777ef92c
Revises: 8f97975fec5c
Create Date: 2025-10-21 22:30:45.388243

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e533777ef92c'
down_revision: Union[str, Sequence[str], None] = '8f97975fec5c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'users',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('clerk_user_id', sa.String(255), nullable=False, unique=True),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
    )
    op.create_index('idx_users_clerk_id', 'users', ['clerk_user_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_users_clerk_id', 'users')
    op.drop_table('users')
