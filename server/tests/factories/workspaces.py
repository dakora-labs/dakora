"""Workspace factory for creating test workspaces."""

from uuid import UUID
from typing import Optional
from sqlalchemy import insert, select
from sqlalchemy.engine import Connection

from dakora_server.core.database import workspaces_table, workspace_members_table
from .constants import (
    TEST_WORKSPACE_ID,
    TEST_WORKSPACE_SLUG,
    TEST_WORKSPACE_NAME,
    make_test_workspace_id,
)
from .users import create_test_user


def create_test_workspace(
    conn: Connection,
    workspace_id: Optional[UUID] = None,
    slug: Optional[str] = None,
    name: Optional[str] = None,
    workspace_type: str = "personal",
    owner_id: Optional[UUID] = None,
    suffix: Optional[str] = None,
    create_owner: bool = True,
) -> tuple[UUID, UUID]:
    """Create a test workspace in the database.

    Args:
        conn: Database connection
        workspace_id: Workspace UUID (defaults to TEST_WORKSPACE_ID or generated from suffix)
        slug: Workspace slug (defaults to TEST_WORKSPACE_SLUG or generated from suffix)
        name: Workspace name (defaults to TEST_WORKSPACE_NAME)
        workspace_type: Workspace type ("personal" or "team")
        owner_id: Owner user UUID (creates default user if not provided and create_owner=True)
        suffix: Suffix for generating unique IDs
        create_owner: Whether to auto-create owner user if not provided

    Returns:
        Tuple of (workspace_id, owner_id)

    Example:
        # Default workspace with auto-created owner
        workspace_id, owner_id = create_test_workspace(conn)

        # Workspace with existing owner
        user_id = create_test_user(conn)
        workspace_id, _ = create_test_workspace(conn, owner_id=user_id)

        # Multiple workspaces
        ws1_id, owner1 = create_test_workspace(conn, suffix="1")
        ws2_id, owner2 = create_test_workspace(conn, suffix="2")
    """
    if suffix:
        workspace_id = make_test_workspace_id(suffix)
        slug = f"test-workspace-{suffix}"
        name = f"Test Workspace {suffix}"
    else:
        workspace_id = workspace_id or TEST_WORKSPACE_ID
        slug = slug or TEST_WORKSPACE_SLUG
        name = name or TEST_WORKSPACE_NAME

    # Create owner if needed
    if owner_id is None and create_owner:
        owner_id = create_test_user(conn, suffix=suffix)

    if owner_id is None:
        raise ValueError("owner_id must be provided or create_owner must be True")

    # Check if workspace already exists
    existing = conn.execute(
        select(workspaces_table.c.id).where(workspaces_table.c.id == workspace_id)
    ).fetchone()

    if existing:
        return workspace_id, owner_id

    # Create workspace
    conn.execute(
        insert(workspaces_table).values(
            id=workspace_id,
            slug=slug,
            name=name,
            type=workspace_type,
            owner_id=owner_id,
        )
    )

    # Add owner as member
    conn.execute(
        insert(workspace_members_table).values(
            workspace_id=workspace_id,
            user_id=owner_id,
            role="owner",
        )
    )

    return workspace_id, owner_id
