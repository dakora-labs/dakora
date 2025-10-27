"""merge versioning and trace source columns

Revision ID: 137ea41e265f
Revises: e6ef5938d4d0, 6f3c2d51a9ab
Create Date: 2025-10-27 12:08:02.837246

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '137ea41e265f'
down_revision: Union[str, Sequence[str], None] = ('e6ef5938d4d0', '6f3c2d51a9ab')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
