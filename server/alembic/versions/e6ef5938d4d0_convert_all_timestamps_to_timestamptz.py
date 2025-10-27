"""convert all timestamps to timestamptz

Revision ID: e6ef5938d4d0
Revises: 5dcc8a019533
Create Date: 2025-10-27 10:21:56.781297

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e6ef5938d4d0'
down_revision: Union[str, Sequence[str], None] = '5dcc8a019533'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Convert all timestamp columns to timestamptz with UTC defaults."""

    # logs table
    op.alter_column('logs', 'created_at',
                   type_=sa.DateTime(timezone=True),
                   server_default=sa.text("(NOW() AT TIME ZONE 'UTC')"),
                   existing_nullable=True)

    # users table
    op.alter_column('users', 'created_at',
                   type_=sa.DateTime(timezone=True),
                   server_default=sa.text("(NOW() AT TIME ZONE 'UTC')"),
                   existing_nullable=False)

    # workspaces table
    op.alter_column('workspaces', 'created_at',
                   type_=sa.DateTime(timezone=True),
                   server_default=sa.text("(NOW() AT TIME ZONE 'UTC')"),
                   existing_nullable=False)

    # workspace_members table
    op.alter_column('workspace_members', 'joined_at',
                   type_=sa.DateTime(timezone=True),
                   server_default=sa.text("(NOW() AT TIME ZONE 'UTC')"),
                   existing_nullable=False)

    # projects table
    op.alter_column('projects', 'created_at',
                   type_=sa.DateTime(timezone=True),
                   server_default=sa.text("(NOW() AT TIME ZONE 'UTC')"),
                   existing_nullable=False)
    op.alter_column('projects', 'updated_at',
                   type_=sa.DateTime(timezone=True),
                   server_default=sa.text("(NOW() AT TIME ZONE 'UTC')"),
                   existing_nullable=False)

    # prompts table
    op.alter_column('prompts', 'last_updated_at',
                   type_=sa.DateTime(timezone=True),
                   server_default=sa.text("(NOW() AT TIME ZONE 'UTC')"),
                   existing_nullable=False)
    op.alter_column('prompts', 'created_at',
                   type_=sa.DateTime(timezone=True),
                   server_default=sa.text("(NOW() AT TIME ZONE 'UTC')"),
                   existing_nullable=False)

    # prompt_versions table - already has UTC, just convert to timestamptz
    op.alter_column('prompt_versions', 'created_at',
                   type_=sa.DateTime(timezone=True),
                   server_default=sa.text("(NOW() AT TIME ZONE 'UTC')"),
                   existing_nullable=False)

    # prompt_parts table
    op.alter_column('prompt_parts', 'created_at',
                   type_=sa.DateTime(timezone=True),
                   server_default=sa.text("(NOW() AT TIME ZONE 'UTC')"),
                   existing_nullable=False)
    op.alter_column('prompt_parts', 'updated_at',
                   type_=sa.DateTime(timezone=True),
                   server_default=sa.text("(NOW() AT TIME ZONE 'UTC')"),
                   existing_nullable=False)

    # api_keys table
    op.alter_column('api_keys', 'created_at',
                   type_=sa.DateTime(timezone=True),
                   server_default=sa.text("(NOW() AT TIME ZONE 'UTC')"),
                   existing_nullable=False)
    op.alter_column('api_keys', 'last_used_at',
                   type_=sa.DateTime(timezone=True),
                   existing_nullable=True)
    op.alter_column('api_keys', 'expires_at',
                   type_=sa.DateTime(timezone=True),
                   existing_nullable=True)
    op.alter_column('api_keys', 'revoked_at',
                   type_=sa.DateTime(timezone=True),
                   existing_nullable=True)

    # workspace_quotas table
    op.alter_column('workspace_quotas', 'current_period_start',
                   type_=sa.DateTime(timezone=True),
                   existing_nullable=False)
    op.alter_column('workspace_quotas', 'current_period_end',
                   type_=sa.DateTime(timezone=True),
                   existing_nullable=False)
    op.alter_column('workspace_quotas', 'created_at',
                   type_=sa.DateTime(timezone=True),
                   server_default=sa.text("(NOW() AT TIME ZONE 'UTC')"),
                   existing_nullable=False)
    op.alter_column('workspace_quotas', 'updated_at',
                   type_=sa.DateTime(timezone=True),
                   server_default=sa.text("(NOW() AT TIME ZONE 'UTC')"),
                   existing_nullable=False)

    # prompt_executions table
    op.alter_column('prompt_executions', 'created_at',
                   type_=sa.DateTime(timezone=True),
                   server_default=sa.text("(NOW() AT TIME ZONE 'UTC')"),
                   existing_nullable=False)

    # optimization_runs table
    op.alter_column('optimization_runs', 'created_at',
                   type_=sa.DateTime(timezone=True),
                   server_default=sa.text("(NOW() AT TIME ZONE 'UTC')"),
                   existing_nullable=False)


def downgrade() -> None:
    """Convert all timestamptz columns back to timestamp without time zone."""

    # optimization_runs table
    op.alter_column('optimization_runs', 'created_at',
                   type_=sa.DateTime(timezone=False),
                   server_default=sa.text("NOW()"),
                   existing_nullable=False)

    # prompt_executions table
    op.alter_column('prompt_executions', 'created_at',
                   type_=sa.DateTime(timezone=False),
                   server_default=sa.text("NOW()"),
                   existing_nullable=False)

    # workspace_quotas table
    op.alter_column('workspace_quotas', 'updated_at',
                   type_=sa.DateTime(timezone=False),
                   server_default=sa.text("NOW()"),
                   existing_nullable=False)
    op.alter_column('workspace_quotas', 'created_at',
                   type_=sa.DateTime(timezone=False),
                   server_default=sa.text("NOW()"),
                   existing_nullable=False)
    op.alter_column('workspace_quotas', 'current_period_end',
                   type_=sa.DateTime(timezone=False),
                   existing_nullable=False)
    op.alter_column('workspace_quotas', 'current_period_start',
                   type_=sa.DateTime(timezone=False),
                   existing_nullable=False)

    # api_keys table
    op.alter_column('api_keys', 'revoked_at',
                   type_=sa.DateTime(timezone=False),
                   existing_nullable=True)
    op.alter_column('api_keys', 'expires_at',
                   type_=sa.DateTime(timezone=False),
                   existing_nullable=True)
    op.alter_column('api_keys', 'last_used_at',
                   type_=sa.DateTime(timezone=False),
                   existing_nullable=True)
    op.alter_column('api_keys', 'created_at',
                   type_=sa.DateTime(timezone=False),
                   server_default=sa.text("NOW()"),
                   existing_nullable=False)

    # prompt_parts table
    op.alter_column('prompt_parts', 'updated_at',
                   type_=sa.DateTime(timezone=False),
                   server_default=sa.text("NOW()"),
                   existing_nullable=False)
    op.alter_column('prompt_parts', 'created_at',
                   type_=sa.DateTime(timezone=False),
                   server_default=sa.text("NOW()"),
                   existing_nullable=False)

    # prompt_versions table
    op.alter_column('prompt_versions', 'created_at',
                   type_=sa.DateTime(timezone=False),
                   server_default=sa.text("(NOW() AT TIME ZONE 'UTC')"),
                   existing_nullable=False)

    # prompts table
    op.alter_column('prompts', 'created_at',
                   type_=sa.DateTime(timezone=False),
                   server_default=sa.text("NOW()"),
                   existing_nullable=False)
    op.alter_column('prompts', 'last_updated_at',
                   type_=sa.DateTime(timezone=False),
                   server_default=sa.text("NOW()"),
                   existing_nullable=False)

    # projects table
    op.alter_column('projects', 'updated_at',
                   type_=sa.DateTime(timezone=False),
                   server_default=sa.text("NOW()"),
                   existing_nullable=False)
    op.alter_column('projects', 'created_at',
                   type_=sa.DateTime(timezone=False),
                   server_default=sa.text("NOW()"),
                   existing_nullable=False)

    # workspace_members table
    op.alter_column('workspace_members', 'joined_at',
                   type_=sa.DateTime(timezone=False),
                   server_default=sa.text("NOW()"),
                   existing_nullable=False)

    # workspaces table
    op.alter_column('workspaces', 'created_at',
                   type_=sa.DateTime(timezone=False),
                   server_default=sa.text("NOW()"),
                   existing_nullable=False)

    # users table
    op.alter_column('users', 'created_at',
                   type_=sa.DateTime(timezone=False),
                   server_default=sa.text("NOW()"),
                   existing_nullable=False)

    # logs table
    op.alter_column('logs', 'created_at',
                   type_=sa.DateTime(timezone=False),
                   server_default=sa.text("CURRENT_TIMESTAMP"),
                   existing_nullable=True)