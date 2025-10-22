"""Auto-provisioning logic for workspaces and projects."""

from typing import Optional
from uuid import UUID
import re
from sqlalchemy.engine import Engine, Connection
from sqlalchemy import select, insert

from .database import get_connection


def generate_slug(name: str) -> str:
    """Generate URL-friendly slug from name.

    Args:
        name: User's name or email

    Returns:
        URL-safe slug (lowercase, alphanumeric + hyphens)
    """
    if not name or not name.strip():
        return "user"

    # Extract first name if multiple words (for workspace slug purposes)
    parts = name.split()
    if not parts:
        return "user"

    first_name = parts[0]

    # Convert to lowercase and replace spaces/special chars with hyphens
    slug = re.sub(r'[^a-z0-9]+', '-', first_name.lower())
    slug = slug.strip('-')

    return slug or "user"


def get_first_name(full_name: Optional[str]) -> str:
    """Extract first name from full name.

    Args:
        full_name: Full name string (e.g., "Bogdan Pshonyak")

    Returns:
        First name (e.g., "Bogdan")
    """
    if not full_name:
        return "User"

    # Split on whitespace and take first part
    parts = full_name.split()
    return parts[0] if parts else "User"


def provision_workspace_and_project(
    conn: Connection,
    user_id: UUID,
    user_name: Optional[str],
    user_email: str
) -> tuple[UUID, UUID]:
    """Provision workspace and default project for a new user.

    Creates:
    1. Personal workspace with name "<FirstName>'s Projects"
    2. Workspace membership with owner role
    3. Default project with name "<FirstName>'s Project"

    Args:
        conn: Database connection
        user_id: User's UUID from users table
        user_name: User's full name (optional)
        user_email: User's email address

    Returns:
        Tuple of (workspace_id, project_id)
    """
    from .database import metadata

    # Get table references (will be defined by migration)
    workspaces_table = metadata.tables['workspaces']
    workspace_members_table = metadata.tables['workspace_members']
    projects_table = metadata.tables['projects']

    # Extract first name for display
    first_name = get_first_name(user_name)

    # Generate slug from name or email
    slug_source = user_name if user_name else user_email.split('@')[0]
    base_slug = generate_slug(slug_source)

    # Ensure unique slug (append number if needed)
    slug = base_slug
    counter = 1
    while True:
        existing = conn.execute(
            select(workspaces_table.c.id).where(workspaces_table.c.slug == slug)
        ).fetchone()

        if not existing:
            break

        slug = f"{base_slug}-{counter}"
        counter += 1

    # Create workspace
    workspace_name = f"{first_name}'s Projects"
    result = conn.execute(
        insert(workspaces_table).values(
            slug=slug,
            name=workspace_name,
            type='personal',
            owner_id=user_id
        ).returning(workspaces_table.c.id)
    )
    workspace_id = result.fetchone()[0]

    # Create workspace membership (owner role)
    conn.execute(
        insert(workspace_members_table).values(
            workspace_id=workspace_id,
            user_id=user_id,
            role='owner'
        )
    )

    # Create default project
    project_name = f"{first_name}'s Project"
    result = conn.execute(
        insert(projects_table).values(
            workspace_id=workspace_id,
            slug='default',
            name=project_name,
            description='Default project'
        ).returning(projects_table.c.id)
    )
    project_id = result.fetchone()[0]

    return workspace_id, project_id


def get_or_create_workspace(
    engine: Engine,
    user_id: UUID,
    user_name: Optional[str],
    user_email: str
) -> tuple[UUID, UUID]:
    """Get user's workspace and project, creating them if they don't exist.

    This handles the race condition where:
    - User logs in before Clerk webhook completes
    - Webhook fails and never provisions workspace
    - Manual testing without webhooks

    Args:
        engine: Database engine
        user_id: User's UUID from users table
        user_name: User's full name (optional)
        user_email: User's email address

    Returns:
        Tuple of (workspace_id, project_id)
    """
    from .database import metadata

    with get_connection(engine) as conn:
        # Reload metadata to get tables defined by migrations
        metadata.reflect(bind=conn)

        workspaces_table = metadata.tables['workspaces']
        workspace_members_table = metadata.tables['workspace_members']
        projects_table = metadata.tables['projects']

        # Check if workspace exists
        result = conn.execute(
            select(workspaces_table.c.id).where(
                workspaces_table.c.owner_id == user_id
            )
        ).fetchone()

        if result:
            workspace_id = result[0]

            # Get default project
            project_result = conn.execute(
                select(projects_table.c.id).where(
                    projects_table.c.workspace_id == workspace_id
                ).limit(1)
            ).fetchone()

            if project_result:
                return workspace_id, project_result[0]

        # Workspace doesn't exist, provision it
        workspace_id, project_id = provision_workspace_and_project(
            conn, user_id, user_name, user_email
        )
        conn.commit()

        return workspace_id, project_id