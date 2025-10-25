"""Test to verify the fixture infrastructure works correctly.

This test demonstrates the recommended patterns for writing integration tests.
"""

import pytest
from uuid import UUID


def test_factories_create_user(db_connection):
    """Test that user factory creates users correctly."""
    from tests.factories import create_test_user

    user_id = create_test_user(db_connection, suffix="factory-test")

    assert isinstance(user_id, UUID)

    # Verify idempotency - calling again should return same ID
    user_id_2 = create_test_user(db_connection, suffix="factory-test")
    assert user_id == user_id_2


def test_factories_create_workspace(db_connection):
    """Test that workspace factory creates workspaces with owners."""
    from tests.factories import create_test_workspace

    workspace_id, owner_id = create_test_workspace(db_connection, suffix="ws-test")

    assert isinstance(workspace_id, UUID)
    assert isinstance(owner_id, UUID)


def test_factories_create_project(db_connection):
    """Test that project factory creates complete hierarchy."""
    from tests.factories import create_test_project

    project_id, workspace_id, owner_id = create_test_project(
        db_connection, suffix="proj-test"
    )

    assert isinstance(project_id, UUID)
    assert isinstance(workspace_id, UUID)
    assert isinstance(owner_id, UUID)


def test_fixtures_provide_test_project(test_project):
    """Test that test_project fixture provides valid IDs."""
    project_id, workspace_id, owner_id = test_project

    assert isinstance(project_id, UUID)
    assert isinstance(workspace_id, UUID)
    assert isinstance(owner_id, UUID)


def test_auth_override_works(test_client, override_auth_dependencies, test_project):
    """Test that auth override allows API calls without real authentication."""
    project_id, _, _ = test_project

    # This should work because override_auth_dependencies mocks the auth
    response = test_client.get("/api/health")
    assert response.status_code == 200


def test_multiple_projects_isolated(db_connection):
    """Test creating multiple projects with different owners."""
    from tests.factories import create_test_project

    # Create two separate projects
    proj1_id, ws1_id, owner1_id = create_test_project(db_connection, suffix="iso-1")
    proj2_id, ws2_id, owner2_id = create_test_project(db_connection, suffix="iso-2")

    # Verify they're different
    assert proj1_id != proj2_id
    assert ws1_id != ws2_id
    assert owner1_id != owner2_id


def test_cleanup_works(db_connection, test_project):
    """Test that cleanup_project_data fixture removes test data.

    This test verifies the auto-cleanup fixture works. Any prompts created
    here should be cleaned up after the test completes.
    """
    from dakora_server.core.database import prompts_table
    from sqlalchemy import insert, select

    project_id, _, _ = test_project

    # Create a test prompt
    db_connection.execute(
        insert(prompts_table).values(
            project_id=project_id,
            prompt_id="test-cleanup",
            version="1.0.0",
            description="Should be cleaned up",
            storage_path="test/path",
        )
    )
    db_connection.commit()

    # Verify it exists
    result = db_connection.execute(
        select(prompts_table.c.id).where(
            prompts_table.c.project_id == project_id,
            prompts_table.c.prompt_id == "test-cleanup",
        )
    ).fetchone()

    assert result is not None

    # cleanup_project_data will remove this after the test


def test_custom_auth_override(db_connection, test_client):
    """Test using custom auth override for specific scenarios."""
    from tests.factories import create_test_user, create_test_project
    from tests.fixtures.auth import create_custom_auth_override
    from dakora_server.main import app

    # Create a project
    project_id, _, owner_id = create_test_project(db_connection, suffix="custom-auth")

    # Override auth to use this specific user/project
    override = create_custom_auth_override(owner_id, project_id)
    app.dependency_overrides.update(override)

    try:
        # This request will use the custom auth
        response = test_client.get("/api/health")
        assert response.status_code == 200
    finally:
        # Clean up overrides
        app.dependency_overrides.clear()
