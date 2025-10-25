"""remove_tokens_limit_month_from_workspace_quotas

Revision ID: 4c2252bbbbd9
Revises: cbb4906847c4
Create Date: 2025-10-25 12:04:10.833950

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4c2252bbbbd9'
down_revision: Union[str, Sequence[str], None] = 'cbb4906847c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - remove tokens_limit_month column."""
    op.drop_column('workspace_quotas', 'tokens_limit_month')


def downgrade() -> None:
    """Downgrade schema - restore tokens_limit_month column."""
    op.add_column(
        'workspace_quotas',
        sa.Column('tokens_limit_month', sa.Integer(), nullable=False, server_default='100000')
    )
