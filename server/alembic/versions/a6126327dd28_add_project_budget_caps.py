"""add_project_budget_caps

Revision ID: a6126327dd28
Revises: 137ea41e265f
Create Date: 2025-10-27 17:39:34.483104

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a6126327dd28'
down_revision: Union[str, Sequence[str], None] = '137ea41e265f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add budget tracking columns to projects table."""
    # Add budget columns
    op.add_column('projects', sa.Column('budget_monthly_usd', sa.Numeric(10, 2), nullable=True))
    op.add_column('projects', sa.Column('alert_threshold_pct', sa.Integer(), server_default='80', nullable=False))
    op.add_column('projects', sa.Column('budget_enforcement_mode', sa.String(20), server_default='strict', nullable=False))

    # Add index for budget queries on execution_traces
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_traces_budget_calc
        ON execution_traces (project_id, created_at, cost_usd)
        WHERE cost_usd IS NOT NULL
    """)


def downgrade() -> None:
    """Remove budget tracking columns from projects table."""
    # Drop index
    op.execute("DROP INDEX IF EXISTS idx_traces_budget_calc")

    # Drop columns
    op.drop_column('projects', 'budget_enforcement_mode')
    op.drop_column('projects', 'alert_threshold_pct')
    op.drop_column('projects', 'budget_monthly_usd')
