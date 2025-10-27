"""rename tables to traces nomenclature

Revision ID: d2d3a7eb0491
Revises: 50431352eafc
Create Date: 2025-10-25 22:39:30.070510

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'd2d3a7eb0491'
down_revision: Union[str, Sequence[str], None] = '50431352eafc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename tables to use traces nomenclature."""
    # Rename logs table to execution_traces
    op.rename_table('logs', 'execution_traces')
    
    # Rename template_executions table to template_traces
    op.rename_table('template_executions', 'template_traces')
    
    # Note: Foreign key constraints are automatically renamed by PostgreSQL
    # The FK from template_traces.trace_id -> execution_traces.trace_id will work


def downgrade() -> None:
    """Revert table renames."""
    # Reverse the renames
    op.rename_table('template_traces', 'template_executions')
    op.rename_table('execution_traces', 'logs')
