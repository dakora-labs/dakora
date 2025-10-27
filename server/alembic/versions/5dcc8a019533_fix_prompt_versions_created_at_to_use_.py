"""fix prompt_versions created_at to use UTC

Revision ID: 5dcc8a019533
Revises: f7c464629f4d
Create Date: 2025-10-27 10:10:46.914412

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5dcc8a019533'
down_revision: Union[str, Sequence[str], None] = 'f7c464629f4d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        'prompt_versions',
        'created_at',
        server_default=sa.text("(NOW() AT TIME ZONE 'UTC')"),
        existing_type=sa.DateTime(),
        existing_nullable=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        'prompt_versions',
        'created_at',
        server_default=sa.text("NOW()"),
        existing_type=sa.DateTime(),
        existing_nullable=False,
    )
