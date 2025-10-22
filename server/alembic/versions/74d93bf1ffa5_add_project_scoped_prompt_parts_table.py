"""Add project-scoped prompt_parts table

Revision ID: 74d93bf1ffa5
Revises: d14691384760
Create Date: 2025-10-22 17:05:20.806581

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '74d93bf1ffa5'
down_revision: Union[str, Sequence[str], None] = 'd14691384760'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create the table
    op.create_table(
        'prompt_parts',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('project_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('part_id', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=63), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('project_id', 'part_id', name='unique_project_part')
    )
    op.create_index('idx_prompt_parts_project', 'prompt_parts', ['project_id'])

    # Seed common prompt parts for all existing projects
    # Note: New projects will need to add parts manually or via API
    conn = op.get_bind()

    # Get all project IDs
    projects = conn.execute(sa.text("SELECT id FROM projects")).fetchall()

    # Seed data for each project
    for project_row in projects:
        project_id = project_row[0]

        # Common prompt parts that are useful across projects
        seed_parts = [
            {
                'project_id': project_id,
                'part_id': 'system_role',
                'category': 'system_roles',
                'name': 'System Role',
                'description': 'Defines the persona or role the AI should adopt.',
                'content': 'You are a helpful AI assistant.'
            },
            {
                'project_id': project_id,
                'part_id': 'json_output',
                'category': 'formatting',
                'name': 'JSON Output',
                'description': 'Instructs the model to format the output as JSON.',
                'content': 'Format your response as valid JSON.'
            },
            {
                'project_id': project_id,
                'part_id': 'markdown_list',
                'category': 'formatting',
                'name': 'Markdown List',
                'description': 'Requests a list formatted in markdown.',
                'content': 'Format your response as a markdown list.'
            },
            {
                'project_id': project_id,
                'part_id': 'chain_of_thought',
                'category': 'reasoning',
                'name': 'Chain of Thought',
                'description': 'Enables step-by-step reasoning.',
                'content': "Think through this step by step:\n1. Analyze the problem\n2. Break it into smaller parts\n3. Solve each part\n4. Combine the solutions"
            },
        ]

        for part in seed_parts:
            conn.execute(
                sa.text("""
                    INSERT INTO prompt_parts
                    (project_id, part_id, category, name, description, content)
                    VALUES (:project_id, :part_id, :category, :name, :description, :content)
                """),
                part
            )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_prompt_parts_project', table_name='prompt_parts')
    op.drop_table('prompt_parts')
