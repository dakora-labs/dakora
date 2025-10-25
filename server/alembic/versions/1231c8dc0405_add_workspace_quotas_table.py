"""add workspace quotas table

Revision ID: 1231c8dc0405
Revises: 80ca7cf8295a
Create Date: 2025-10-24 12:49:09.987008

"""
from typing import Sequence, Union
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '1231c8dc0405'
down_revision: Union[str, Sequence[str], None] = '80ca7cf8295a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create workspace_quotas table
    op.create_table(
        'workspace_quotas',
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('tier', sa.String(50), nullable=False, server_default='free'),
        sa.Column('tokens_used_month', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('tokens_limit_month', sa.Integer(), nullable=False),
        sa.Column('current_period_start', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('current_period_end', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('workspace_id'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
    )
    op.create_index('idx_workspace_quotas_workspace', 'workspace_quotas', ['workspace_id'])

    # Seed quotas for existing workspaces
    conn = op.get_bind()

    # Calculate current period dates
    now = datetime.now(timezone.utc)
    period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if now.month == 12:
        period_end = period_start.replace(year=now.year + 1, month=1)
    else:
        period_end = period_start.replace(month=now.month + 1)

    # Free tier limit
    free_tier_limit = 100_000

    # Insert quota for all existing workspaces
    conn.execute(
        text("""
            INSERT INTO workspace_quotas
            (workspace_id, tier, tokens_used_month, tokens_limit_month,
             current_period_start, current_period_end)
            SELECT id, 'free', 0, :tokens_limit, :period_start, :period_end
            FROM workspaces
        """),
        {
            "tokens_limit": free_tier_limit,
            "period_start": period_start,
            "period_end": period_end,
        },
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_workspace_quotas_workspace', table_name='workspace_quotas')
    op.drop_table('workspace_quotas')
