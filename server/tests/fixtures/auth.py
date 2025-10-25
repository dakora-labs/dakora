"""Authentication fixtures for testing.

Provides auth context mocking using FastAPI dependency overrides.
NEVER use monkey patching for auth - always use dependency overrides.
"""

import pytest
from typing import Generator, Optional
from uuid import UUID

from dakora_server.auth import (
    get_auth_context,
    validate_project_access,
    get_current_user_id,
    AuthContext,
)
from dakora_server.main import app


class TestAuthContext:
    """Container for test authentication context.

    Allows tests to customize which user/project they're authenticated as.
    """

    def __init__(
        self,
        user_id: UUID,
        workspace_id: UUID,
        project_id: UUID,
        clerk_user_id: str = "test_clerk_user",
    ):
        self.user_id = user_id
        self.workspace_id = workspace_id
        self.project_id = project_id
        self.clerk_user_id = clerk_user_id

    def as_auth_context(self) -> AuthContext:
        """Convert to FastAPI AuthContext."""
        return AuthContext(
            user_id=str(self.user_id),
            project_id=str(self.project_id),
            auth_method="test",
        )


@pytest.fixture
def auth_context(test_project) -> TestAuthContext:
    """Provide authentication context for tests.

    Returns TestAuthContext with user_id, workspace_id, and project_id
    from the test_project fixture.

    Example:
        def test_with_auth(auth_context):
            assert auth_context.user_id is not None
            assert auth_context.project_id is not None
    """
    project_id, workspace_id, owner_id = test_project
    return TestAuthContext(
        user_id=owner_id,
        workspace_id=workspace_id,
        project_id=project_id,
    )


@pytest.fixture
def override_auth_dependencies(auth_context: TestAuthContext) -> Generator[None, None, None]:
    """Override FastAPI auth dependencies with test auth context.

    This fixture uses FastAPI's dependency_overrides to inject test auth
    instead of monkey patching. This is the correct way to mock dependencies.

    The fixture automatically clears overrides after the test completes.

    Example:
        def test_api_endpoint(test_client, override_auth_dependencies):
            # Auth is now mocked - API calls will use test user/project
            response = test_client.get("/api/projects/...")
            assert response.status_code == 200
    """
    # Override get_auth_context to return test auth
    async def mock_get_auth_context() -> AuthContext:
        return auth_context.as_auth_context()

    # Override validate_project_access to return test project
    async def mock_validate_project_access(project_id: str) -> UUID:
        # In tests, we trust the provided project_id matches auth_context
        return auth_context.project_id

    # Override get_current_user_id to return test user
    async def mock_get_current_user_id() -> UUID:
        return auth_context.user_id

    # Apply overrides
    app.dependency_overrides[get_auth_context] = mock_get_auth_context
    app.dependency_overrides[validate_project_access] = mock_validate_project_access
    app.dependency_overrides[get_current_user_id] = mock_get_current_user_id

    yield

    # Clear overrides after test
    app.dependency_overrides.clear()


def create_custom_auth_override(
    user_id: UUID,
    project_id: UUID,
    clerk_user_id: str = "test_clerk_user",
):
    """Create a custom auth override for specific test scenarios.

    Use this when you need to test with a specific user/project that differs
    from the default test fixtures.

    Example:
        def test_unauthorized_access(db_connection):
            # Create a different user
            other_user_id = create_test_user(db_connection, suffix="other")
            project_id, _, _ = create_test_project(db_connection)

            # Override auth with this different user
            override = create_custom_auth_override(other_user_id, project_id)
            app.dependency_overrides.update(override)

            # Test that this user can't access resources
            response = test_client.get(f"/api/projects/{project_id}/...")
            assert response.status_code == 403

            app.dependency_overrides.clear()
    """
    async def mock_get_auth_context() -> AuthContext:
        return AuthContext(
            user_id=str(user_id),
            project_id=str(project_id),
            auth_method="test",
        )

    async def mock_validate_project_access(proj_id: str) -> UUID:
        return project_id

    async def mock_get_current_user_id() -> UUID:
        return user_id

    return {
        get_auth_context: mock_get_auth_context,
        validate_project_access: mock_validate_project_access,
        get_current_user_id: mock_get_current_user_id,
    }
