"""merge heads

Revision ID: f7f2cd6d0a06
Revises: 12c129dba326, d2d3a7eb0491
Create Date: 2025-10-26 18:26:47.846757

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7f2cd6d0a06'
down_revision: Union[str, Sequence[str], None] = ('12c129dba326', 'd2d3a7eb0491')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
