"""Stable test constants for predictable test data.

These constants provide stable UUIDs and IDs that can be reused across tests
to maintain referential integrity without random UUID generation.
"""

from uuid import UUID, uuid5, NAMESPACE_DNS

# Stable UUIDs for default test entities
# Using UUID5 with DNS namespace ensures reproducible IDs
TEST_USER_ID = uuid5(NAMESPACE_DNS, "test-user-default")
TEST_WORKSPACE_ID = uuid5(NAMESPACE_DNS, "test-workspace-default")
TEST_PROJECT_ID = uuid5(NAMESPACE_DNS, "test-project-default")

# Test user identifiers
TEST_CLERK_USER_ID = "test_clerk_user_default"
TEST_USER_EMAIL = "test@example.com"
TEST_USER_NAME = "Test User"

# Test workspace identifiers
TEST_WORKSPACE_SLUG = "test-workspace"
TEST_WORKSPACE_NAME = "Test Workspace"

# Test project identifiers
TEST_PROJECT_SLUG = "test-project"
TEST_PROJECT_NAME = "Test Project"
TEST_PROJECT_DESCRIPTION = "Default test project for integration tests"


def make_test_user_id(suffix: str) -> UUID:
    """Generate a stable UUID for a test user with suffix."""
    return uuid5(NAMESPACE_DNS, f"test-user-{suffix}")


def make_test_workspace_id(suffix: str) -> UUID:
    """Generate a stable UUID for a test workspace with suffix."""
    return uuid5(NAMESPACE_DNS, f"test-workspace-{suffix}")


def make_test_project_id(suffix: str) -> UUID:
    """Generate a stable UUID for a test project with suffix."""
    return uuid5(NAMESPACE_DNS, f"test-project-{suffix}")
