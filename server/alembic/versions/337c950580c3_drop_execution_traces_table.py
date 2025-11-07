"""drop_execution_traces_table

Revision ID: 337c950580c3
Revises: 288bb30b3909
Create Date: 2025-11-05 22:02:03.262847

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '337c950580c3'
down_revision: Union[str, Sequence[str], None] = '288bb30b3909'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Drop the old execution_traces table.
    Clean break - no backward compatibility, no downgrade.
    """
    # Drop the old execution_traces table
    op.drop_table("execution_traces")


def downgrade() -> None:
    """No downgrade - this is a one-way migration."""
    raise NotImplementedError("No downgrade path - execution_traces table is permanently dropped")
