"""add_provider_and_model_indexes

Revision ID: cc4d572fe94a
Revises: 8beb08b837ba
Create Date: 2025-11-04 20:26:43.035449

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cc4d572fe94a'
down_revision: Union[str, Sequence[str], None] = '8beb08b837ba'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add index on lower(provider) for exact match filtering
    op.create_index(
        "idx_executions_provider_lower",
        "executions",
        [sa.text("lower(provider)")],
        unique=False,
        postgresql_using="btree",
    )
    
    # Add GIN trigram index on lower(model) for partial/fuzzy matching with ILIKE
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
    op.create_index(
        "idx_executions_model_trgm",
        "executions",
        [sa.text("lower(model)")],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"lower(model)": "gin_trgm_ops"},
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("idx_executions_model_trgm", table_name="executions", postgresql_using="gin")
    op.drop_index("idx_executions_provider_lower", table_name="executions", postgresql_using="btree")
