"""merge migration heads

Revision ID: 50431352eafc
Revises: 4c2252bbbbd9, a1b2c3d4e5f6
Create Date: 2025-10-25 22:39:23.449060

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '50431352eafc'
down_revision: Union[str, Sequence[str], None] = ('4c2252bbbbd9', 'a1b2c3d4e5f6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
