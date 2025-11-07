"""merge_branches_337c_and_ecbcf

Revision ID: f153c7370ee7
Revises: 337c950580c3, ecbcf45f7a59
Create Date: 2025-11-07 11:52:09.874184

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f153c7370ee7'
down_revision: Union[str, Sequence[str], None] = ('337c950580c3', 'ecbcf45f7a59')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
