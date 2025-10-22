"""Add prompts table

Revision ID: d14691384760
Revises: 75e0887b5bb7
Create Date: 2025-10-22 13:09:54.123108

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd14691384760'
down_revision: Union[str, Sequence[str], None] = '75e0887b5bb7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create prompts table
    op.create_table(
        'prompts',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('project_id', sa.UUID(), nullable=False),
        sa.Column('prompt_id', sa.String(length=255), nullable=False),
        sa.Column('version', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('storage_path', sa.Text(), nullable=False),
        sa.Column('last_updated_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('metadata', sa.dialects.postgresql.JSONB(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id', 'prompt_id', name='uq_prompts_project_prompt_id')
    )
    op.create_index('idx_prompts_project', 'prompts', ['project_id'])
    op.create_index('idx_prompts_updated', 'prompts', ['last_updated_at'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_prompts_updated', table_name='prompts')
    op.drop_index('idx_prompts_project', table_name='prompts')
    op.drop_table('prompts')
