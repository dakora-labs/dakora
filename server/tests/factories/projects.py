"""Project factory for creating test projects."""

from uuid import UUID
from typing import Optional
from sqlalchemy import insert, select
from sqlalchemy.engine import Connection

from dakora_server.core.database import projects_table
from .constants import (
    TEST_PROJECT_ID,
    TEST_PROJECT_SLUG,
    TEST_PROJECT_NAME,
    TEST_PROJECT_DESCRIPTION,
    make_test_project_id,
)
from .workspaces import create_test_workspace


def create_test_project(
    conn: Connection,
    project_id: Optional[UUID] = None,
    slug: Optional[str] = None,
    name: Optional[str] = None,
    description: Optional[str] = None,
    workspace_id: Optional[UUID] = None,
    suffix: Optional[str] = None,
    create_workspace: bool = True,
) -> tuple[UUID, UUID, UUID]:
    """Create a test project in the database.

    Args:
        conn: Database connection
        project_id: Project UUID (defaults to TEST_PROJECT_ID or generated from suffix)
        slug: Project slug (defaults to TEST_PROJECT_SLUG or generated from suffix)
        name: Project name (defaults to TEST_PROJECT_NAME)
        description: Project description (defaults to TEST_PROJECT_DESCRIPTION)
        workspace_id: Workspace UUID (creates default workspace if not provided and create_workspace=True)
        suffix: Suffix for generating unique IDs
        create_workspace: Whether to auto-create workspace if not provided

    Returns:
        Tuple of (project_id, workspace_id, owner_id)

    Example:
        # Default project with auto-created workspace and owner
        project_id, workspace_id, owner_id = create_test_project(conn)

        # Project in existing workspace
        workspace_id, owner_id = create_test_workspace(conn)
        project_id, _, _ = create_test_project(conn, workspace_id=workspace_id)

        # Multiple projects in same workspace
        workspace_id, owner_id = create_test_workspace(conn)
        proj1_id, _, _ = create_test_project(conn, workspace_id=workspace_id, suffix="1")
        proj2_id, _, _ = create_test_project(conn, workspace_id=workspace_id, suffix="2")
    """
    if suffix:
        project_id = make_test_project_id(suffix)
        slug = f"test-project-{suffix}"
        name = f"Test Project {suffix}"
    else:
        project_id = project_id or TEST_PROJECT_ID
        slug = slug or TEST_PROJECT_SLUG
        name = name or TEST_PROJECT_NAME
        description = description or TEST_PROJECT_DESCRIPTION

    # Create workspace if needed
    owner_id: Optional[UUID] = None
    if workspace_id is None and create_workspace:
        workspace_id, owner_id = create_test_workspace(conn, suffix=suffix)

    if workspace_id is None:
        raise ValueError("workspace_id must be provided or create_workspace must be True")

    # Get owner_id if not already set
    if owner_id is None:
        from dakora_server.core.database import workspaces_table
        workspace_row = conn.execute(
            select(workspaces_table.c.owner_id).where(workspaces_table.c.id == workspace_id)
        ).fetchone()
        if workspace_row:
            owner_id = workspace_row[0]
        else:
            raise ValueError(f"Workspace {workspace_id} not found")

    # Check if project already exists
    existing = conn.execute(
        select(projects_table.c.id).where(projects_table.c.id == project_id)
    ).fetchone()

    if existing:
        return project_id, workspace_id, owner_id

    # Create project
    conn.execute(
        insert(projects_table).values(
            id=project_id,
            workspace_id=workspace_id,
            slug=slug,
            name=name,
            description=description,
        )
    )

    return project_id, workspace_id, owner_id
