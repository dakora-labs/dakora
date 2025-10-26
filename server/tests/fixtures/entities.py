"""Entity fixtures for creating test data.

Provides pytest fixtures for users, workspaces, and projects.
These fixtures compose - test_project depends on test_workspace depends on test_user.
"""

import pytest
from typing import Generator
from uuid import UUID
from sqlalchemy import delete
from sqlalchemy.engine import Connection

from dakora_server.core.database import (
    users_table,
    workspaces_table,
    workspace_members_table,
    workspace_quotas_table,
    projects_table,
    prompts_table,
    prompt_parts_table,
    api_keys_table,
    optimization_runs_table,
    prompt_executions_table,
)
from tests.factories import (
    create_test_user,
    create_test_workspace,
    create_test_project,
)


@pytest.fixture(scope="session")
def test_user(db_engine) -> Generator[UUID, None, None]:
    """Create a test user for the entire test session.

    Session-scoped so all tests share the same default user.
    This is fast and avoids unnecessary DB writes.

    Returns:
        User UUID

    Example:
        def test_with_user(test_user):
            assert test_user is not None
    """
    from dakora_server.core.database import get_connection

    with get_connection(db_engine) as conn:
        user_id = create_test_user(conn)
        conn.commit()

    yield user_id

    # Cleanup: Delete user and all related data
    with get_connection(db_engine) as conn:
        conn.execute(delete(users_table).where(users_table.c.id == user_id))
        conn.commit()


@pytest.fixture(scope="session")
def test_workspace(db_engine, test_user: UUID) -> Generator[tuple[UUID, UUID], None, None]:
    """Create a test workspace for the entire test session.

    Session-scoped so all tests share the same default workspace.

    Returns:
        Tuple of (workspace_id, owner_id)

    Example:
        def test_with_workspace(test_workspace):
            workspace_id, owner_id = test_workspace
            assert workspace_id is not None
    """
    from dakora_server.core.database import get_connection

    with get_connection(db_engine) as conn:
        workspace_id, owner_id = create_test_workspace(
            conn, owner_id=test_user, create_owner=False
        )
        conn.commit()

    yield workspace_id, owner_id

    # Cleanup: Delete workspace and related data
    with get_connection(db_engine) as conn:
        conn.execute(delete(workspace_members_table).where(
            workspace_members_table.c.workspace_id == workspace_id
        ))
        conn.execute(delete(workspaces_table).where(workspaces_table.c.id == workspace_id))
        conn.commit()


@pytest.fixture(scope="session")
def test_project(
    db_engine, test_workspace: tuple[UUID, UUID]
) -> Generator[tuple[UUID, UUID, UUID], None, None]:
    """Create a test project for the entire test session.

    Session-scoped so all tests share the same default project.

    Returns:
        Tuple of (project_id, workspace_id, owner_id)

    Example:
        def test_with_project(test_project):
            project_id, workspace_id, owner_id = test_project
            assert project_id is not None

        def test_api_call(test_project, test_client, override_auth_dependencies):
            project_id, _, _ = test_project
            response = test_client.get(f"/api/projects/{project_id}/prompts/")
            assert response.status_code == 200
    """
    from dakora_server.core.database import get_connection

    workspace_id, owner_id = test_workspace

    with get_connection(db_engine) as conn:
        project_id, _, _ = create_test_project(
            conn, workspace_id=workspace_id, create_workspace=False
        )
        conn.commit()

    yield project_id, workspace_id, owner_id

    # Cleanup: Delete project and related data
    with get_connection(db_engine) as conn:
        conn.execute(delete(api_keys_table).where(api_keys_table.c.project_id == project_id))
        conn.execute(delete(prompt_parts_table).where(prompt_parts_table.c.project_id == project_id))
        conn.execute(delete(prompts_table).where(prompts_table.c.project_id == project_id))
        conn.execute(delete(projects_table).where(projects_table.c.id == project_id))
        conn.commit()


@pytest.fixture(autouse=True)
def cleanup_project_data(db_engine, test_project) -> Generator[None, None, None]:
    """Automatically clean up project-specific data after each test.

    This fixture runs after every test to clean up prompts, parts, API keys,
    optimization runs, executions, and reset workspace quota. This allows tests
    to share session-scoped fixtures while keeping data isolated.

    Uses db_engine to create a fresh connection for cleanup, ensuring it sees
    all committed changes from the test regardless of connection state.

    autouse=True means this runs automatically without being requested.
    """
    yield

    project_id, workspace_id, _ = test_project

    # Clean up data created during the test using a fresh connection
    from dakora_server.core.database import get_connection
    from sqlalchemy import update

    with get_connection(db_engine) as conn:
        # Delete project-scoped data
        conn.execute(delete(api_keys_table).where(api_keys_table.c.project_id == project_id))
        conn.execute(delete(prompt_parts_table).where(prompt_parts_table.c.project_id == project_id))
        conn.execute(delete(prompts_table).where(prompts_table.c.project_id == project_id))
        conn.execute(delete(optimization_runs_table).where(optimization_runs_table.c.project_id == project_id))
        conn.execute(delete(prompt_executions_table).where(prompt_executions_table.c.project_id == project_id))

        # Reset workspace quota usage to 0 (but keep the quota record)
        conn.execute(
            update(workspace_quotas_table)
            .where(workspace_quotas_table.c.workspace_id == workspace_id)
            .values(
                optimization_runs_used_month=0,
                tokens_used_month=0,
            )
        )

        conn.commit()
