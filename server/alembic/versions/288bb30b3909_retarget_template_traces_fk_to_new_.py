"""retarget_template_traces_fk_to_new_traces

Revision ID: 288bb30b3909
Revises: cc4d572fe94a
Create Date: 2025-11-05 21:52:11.876590

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '288bb30b3909'
down_revision: Union[str, Sequence[str], None] = 'cc4d572fe94a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Retarget template_traces.trace_id FK from execution_traces to new traces table.
    Clean break - no backward compatibility. Deletes orphaned template_traces.
    """
    
    # Drop the old FK constraint if it exists
    connection = op.get_bind()
    
    # Check if constraint exists and drop it
    result = connection.execute(text("""
        SELECT constraint_name 
        FROM information_schema.table_constraints 
        WHERE table_name = 'template_traces' 
        AND constraint_type = 'FOREIGN KEY'
        AND constraint_name LIKE '%trace_id%'
    """))
    
    for row in result:
        op.drop_constraint(str(row[0]), "template_traces", type_="foreignkey")
    
    # Delete orphaned template_traces rows that don't have a corresponding trace in new schema
    op.execute(text("""
        DELETE FROM template_traces 
        WHERE trace_id NOT IN (SELECT trace_id FROM traces)
    """))
    
    # Add new FK constraint pointing to traces.trace_id
    op.create_foreign_key(
        "template_traces_trace_id_fkey",
        "template_traces",
        "traces",
        ["trace_id"],
        ["trace_id"],
        ondelete="CASCADE"
    )


def downgrade() -> None:
    """No downgrade - clean break migration."""
    raise NotImplementedError("No downgrade path - this is a one-way migration")
