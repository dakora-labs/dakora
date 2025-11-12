"""add_invitation_requests_table

Revision ID: e09acd469ec7
Revises: f153c7370ee7
Create Date: 2025-11-12 18:29:41.748556

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e09acd469ec7'
down_revision: Union[str, Sequence[str], None] = 'f153c7370ee7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create invitation_requests table."""
    op.create_table(
        'invitation_requests',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('company', sa.String(length=255), nullable=True),
        sa.Column('use_case', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), server_default=sa.text("'pending'"), nullable=False),
        sa.Column('requested_at', sa.TIMESTAMP(timezone=True), server_default=sa.text("(NOW() AT TIME ZONE 'UTC')"), nullable=False),
        sa.Column('reviewed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('reviewed_by', sa.UUID(), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('clerk_invitation_id', sa.String(length=255), nullable=True),
        sa.Column('metadata', sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_invitation_requests_email', 'invitation_requests', ['email'])
    op.create_index('idx_invitation_requests_status', 'invitation_requests', ['status'])
    op.create_index('idx_invitation_requests_requested_at', 'invitation_requests', ['requested_at'])
    op.create_foreign_key('fk_invitation_requests_reviewed_by', 'invitation_requests', 'users', ['reviewed_by'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    """Drop invitation_requests table."""
    op.drop_constraint('fk_invitation_requests_reviewed_by', 'invitation_requests', type_='foreignkey')
    op.drop_index('idx_invitation_requests_requested_at', 'invitation_requests')
    op.drop_index('idx_invitation_requests_status', 'invitation_requests')
    op.drop_index('idx_invitation_requests_email', 'invitation_requests')
    op.drop_table('invitation_requests')
