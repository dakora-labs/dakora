"""add_project_id_to_executions_table

Add project_id column to executions table for direct filtering without joining traces.

This improves query performance by:
- Enabling direct project_id filtering on executions
- Eliminating the need to join with traces table for project-scoped queries
- Adding an index on (project_id, start_time) for efficient time-series queries

Revision ID: bd52ef259a6f
Revises: 9e7ff715964b
Create Date: 2025-11-04 12:52:16.577742

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'bd52ef259a6f'
down_revision: Union[str, Sequence[str], None] = '9e7ff715964b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add project_id column to executions table."""
    
    # Step 1: Add project_id column (nullable initially to allow backfill)
    op.add_column(
        'executions',
        sa.Column('project_id', UUID(as_uuid=True), nullable=True)
    )
    
    # Step 2: Backfill project_id from traces table
    op.execute("""
        UPDATE executions e
        SET project_id = t.project_id
        FROM traces t
        WHERE e.trace_id = t.trace_id
    """)
    
    # Step 3: Make column NOT NULL after backfill
    op.alter_column('executions', 'project_id', nullable=False)
    
    # Step 4: Add foreign key constraint
    op.create_foreign_key(
        'fk_executions_project_id',
        'executions',
        'projects',
        ['project_id'],
        ['id'],
        ondelete='CASCADE'
    )
    
    # Step 5: Add index for efficient project-scoped time-series queries
    op.create_index(
        'idx_executions_project_time',
        'executions',
        ['project_id', sa.text('start_time DESC')]
    )


def downgrade() -> None:
    """Remove project_id column from executions table."""
    
    # Drop index
    op.drop_index('idx_executions_project_time', table_name='executions')
    
    # Drop foreign key
    op.drop_constraint('fk_executions_project_id', 'executions', type_='foreignkey')
    
    # Drop column
    op.drop_column('executions', 'project_id')

