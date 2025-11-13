"""add_unique_constraint_invitation_requests_email_pending

Revision ID: 48c44d904937
Revises: e09acd469ec7
Create Date: 2025-11-13 10:17:46.758409

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '48c44d904937'
down_revision: Union[str, Sequence[str], None] = 'e09acd469ec7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add partial unique index on email for pending invitation requests.
    
    This prevents race conditions where multiple concurrent requests
    for the same email could all create pending records.
    """
    # Create partial unique index: only one pending invitation per email
    op.create_index(
        'idx_invitation_requests_email_pending_unique',
        'invitation_requests',
        ['email'],
        unique=True,
        postgresql_where=sa.text("status = 'pending'")
    )


def downgrade() -> None:
    """Remove partial unique index."""
    op.drop_index(
        'idx_invitation_requests_email_pending_unique',
        'invitation_requests'
    )
