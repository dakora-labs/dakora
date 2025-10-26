# Testing Guide

This guide provides comprehensive information on writing and debugging tests for Dakora. It covers the testing infrastructure, best practices, and common patterns.

## Test Infrastructure

Dakora uses a **layered fixture system** with factory patterns for clean, composable integration tests. This approach avoids monkey patching, uses stable UUIDs, and makes it easy to write new tests without fighting with authentication or database setup.

### Directory Structure

```text
server/tests/
├── conftest.py              # Main fixture registration + legacy fixtures
├── factories/               # Data factories for consistent test entities
│   ├── __init__.py
│   ├── constants.py        # Stable UUIDs (TEST_USER_ID, TEST_PROJECT_ID, etc.)
│   ├── users.py            # create_test_user()
│   ├── workspaces.py       # create_test_workspace()
│   └── projects.py         # create_test_project()
├── fixtures/                # Pytest fixtures
│   ├── __init__.py
│   ├── database.py         # db_engine, db_connection
│   ├── auth.py             # auth_context, override_auth_dependencies
│   └── entities.py         # test_user, test_workspace, test_project
├── integration/            # Integration tests
└── unit/                   # Unit tests
```

## Core Principles

1. **Factory Pattern**: Functions create entities with stable, reproducible UUIDs
2. **FastAPI Dependency Overrides**: NEVER monkey patch - use `app.dependency_overrides`
3. **Composable Fixtures**: `test_project` → `test_workspace` → `test_user`
4. **Session-Scoped Fixtures**: Share user/workspace/project across tests for speed
5. **Auto-Cleanup**: `cleanup_project_data` fixture removes test data after each test
6. **Reuse DB Connections**: Always use `db_connection` fixture - don't create your own connections

## Test Categories & Markers

Dakora uses **pytest markers** to categorize tests and optimize CI runtime:

### Test Categories

- **Unit Tests** - Fast, isolated tests with no database or API calls (default, no marker needed)
- **Integration Tests** - Tests that use database, FastAPI TestClient, or dependency overrides (marked with `@pytest.mark.integration`)
- **Performance Tests** - Slow tests for benchmarking (marked with `@pytest.mark.performance`)

### When to Mark as Integration

Mark tests with `@pytest.mark.integration` if they:
- Use the database (`db_connection`, `test_engine`, or any database fixture)
- Use FastAPI `TestClient` to call API endpoints
- Use `app.dependency_overrides` to mock dependencies
- Hit external services or require Docker containers

### Example

```python
import pytest
from fastapi.testclient import TestClient

@pytest.mark.integration
def test_create_prompt(test_project, test_client, override_auth_dependencies):
    """Integration test that hits the database and API"""
    project_id, _, _ = test_project
    response = test_client.post(f"/api/projects/{project_id}/prompts/", json={...})
    assert response.status_code == 201

@pytest.mark.integration
class TestAPIKeyEndpoints:
    """All tests in this class are integration tests"""

    def test_create_api_key(self, test_client):
        # Uses TestClient and database
        pass
```

### CI Strategy

The CI runs different test categories strategically to optimize runtime:

- **Unit tests**: Run on Python 3.11 and 3.12 (fast, comprehensive)
- **Integration tests**: Run on Python 3.11 only (slower, database required)
- **Coverage**: Runs all tests together for comprehensive coverage report

This approach balances thorough testing with CI speed.

## Running Tests Locally

```bash
# Run all tests (unit + integration)
export PATH="$HOME/.local/bin:$PATH" && uv run python -m pytest

# Run only unit tests (fast - excludes integration & performance)
export PATH="$HOME/.local/bin:$PATH" && uv run python server/tests/test_runner.py unit -v

# Run only integration tests (requires database)
export PATH="$HOME/.local/bin:$PATH" && uv run python server/tests/test_runner.py integration -v

# Run smoke tests (quick validation)
export PATH="$HOME/.local/bin:$PATH" && uv run python server/tests/test_runner.py smoke -v

# Run specific test file
export PATH="$HOME/.local/bin:$PATH" && uv run python -m pytest server/tests/test_database.py -v

# Run specific test function
export PATH="$HOME/.local/bin:$PATH" && uv run python -m pytest server/tests/integration/test_prompts_api.py::test_create_prompt -v

# Run with output (useful for debugging)
export PATH="$HOME/.local/bin:$PATH" && uv run python -m pytest server/tests/ -v -s

# Run without traceback (cleaner output)
export PATH="$HOME/.local/bin:$PATH" && uv run python -m pytest server/tests/ -v --tb=no
```

## Writing Integration Tests

**IMPORTANT**: All integration tests MUST be marked with `@pytest.mark.integration` so CI can run them properly.

### Basic Pattern (Recommended)

```python
import pytest

@pytest.mark.integration
def test_create_prompt(test_project, test_client, override_auth_dependencies):
    """Test creating a prompt via API.

    - test_project: Provides (project_id, workspace_id, owner_id)
    - test_client: FastAPI TestClient
    - override_auth_dependencies: Mocks auth to use test_project's owner
    """
    project_id, _, _ = test_project

    response = test_client.post(
        f"/api/projects/{project_id}/prompts/",
        json={
            "prompt_id": "test-prompt",
            "version": "1.0.0",
            "template": "Hello {{ name }}",
            "inputs": {"name": {"type": "string", "required": True}},
        },
    )

    assert response.status_code == 201
```

### Custom Test Data

```python
@pytest.mark.integration
def test_with_multiple_projects(db_connection):
    """Create custom test entities using factories."""
    from tests.factories import create_test_project

    # Create two projects with stable, predictable IDs
    proj1_id, ws1_id, owner1_id = create_test_project(db_connection, suffix="1")
    proj2_id, ws2_id, owner2_id = create_test_project(db_connection, suffix="2")

    # Test logic here
    assert proj1_id != proj2_id
```

### Custom Auth Context

```python
@pytest.mark.integration
def test_unauthorized_access(db_connection, test_client):
    """Test access control with a different user."""
    from tests.factories import create_test_user, create_test_project
    from tests.fixtures.auth import create_custom_auth_override
    from dakora_server.main import app

    # Create project as one user
    project_id, _, owner_id = create_test_project(db_connection, suffix="owner")

    # Create different user who shouldn't have access
    intruder_id = create_test_user(db_connection, suffix="intruder")

    # Override auth to be the intruder
    override = create_custom_auth_override(intruder_id, project_id)
    app.dependency_overrides.update(override)

    # Test that access is denied
    response = test_client.get(f"/api/projects/{project_id}/prompts/")
    assert response.status_code == 403

    app.dependency_overrides.clear()
```

## Factory Functions

### Available Factories

```python
from tests.factories import (
    create_test_user,
    create_test_workspace,
    create_test_project,
    TEST_USER_ID,          # Stable default UUIDs
    TEST_WORKSPACE_ID,
    TEST_PROJECT_ID,
)

# Create with defaults
user_id = create_test_user(db_connection)

# Create with custom values
user_id = create_test_user(
    db_connection,
    email="custom@example.com",
    name="Custom User",
)

# Create multiple with suffixes (generates stable UUIDs)
user1_id = create_test_user(db_connection, suffix="1")
user2_id = create_test_user(db_connection, suffix="2")

# Factories are idempotent - calling twice with same ID is safe
user_id = create_test_user(db_connection)  # Creates user
user_id = create_test_user(db_connection)  # Returns existing user
```

### Workspace Factory

```python
# Auto-creates owner
workspace_id, owner_id = create_test_workspace(db_connection)

# Use existing owner
user_id = create_test_user(db_connection)
workspace_id, _ = create_test_workspace(
    db_connection,
    owner_id=user_id,
    create_owner=False,
)
```

### Project Factory

```python
# Auto-creates workspace and owner
project_id, workspace_id, owner_id = create_test_project(db_connection)

# Use existing workspace
workspace_id, owner_id = create_test_workspace(db_connection)
project_id, _, _ = create_test_project(
    db_connection,
    workspace_id=workspace_id,
    create_workspace=False,
)

# Multiple projects in same workspace
workspace_id, owner_id = create_test_workspace(db_connection)
proj1_id, _, _ = create_test_project(db_connection, workspace_id=workspace_id, suffix="1")
proj2_id, _, _ = create_test_project(db_connection, workspace_id=workspace_id, suffix="2")
```

## Available Fixtures

### Database Fixtures

- `db_engine` (session-scoped) - Shared database engine
- `db_connection` (function-scoped) - Fresh connection per test, auto-commit/rollback

**IMPORTANT**: Always use the `db_connection` fixture for database operations. Don't create your own database connections.

### Auth Fixtures

- `auth_context` - TestAuthContext with user/workspace/project from test_project
- `override_auth_dependencies` - Overrides FastAPI auth with test_project's owner

### Entity Fixtures

- `test_user` (session-scoped) - Default test user
- `test_workspace` (session-scoped) - Default test workspace
- `test_project` (session-scoped) - Default test project

### Client Fixture

- `test_client` - FastAPI TestClient for API testing

## Authentication in Tests

### Never Monkey Patch Authentication

Use FastAPI's dependency override system:

```python
# ✅ CORRECT: Use dependency overrides
def test_with_auth(test_client, override_auth_dependencies):
    response = test_client.get("/api/projects/...")
    assert response.status_code == 200

# ❌ WRONG: Monkey patching
def test_with_monkey_patch(monkeypatch):
    monkeypatch.setattr("dakora_server.auth.get_auth_context", ...)
```

### Why Dependency Overrides?

- Clean, explicit, and supported by FastAPI
- No side effects or test pollution
- Auto-cleanup when fixture completes
- Type-safe and testable

## Database Management

### Session-Scoped Data

Tests share user/workspace/project fixtures across the entire test session for speed. Each test's changes are cleaned up automatically by `cleanup_project_data`.

### Cleanup Strategy

- `cleanup_project_data` (autouse) - Removes prompts/parts/keys after each test
- Session fixtures clean up on session teardown
- No full DB resets between tests (fast!)

## Best Practices

1. **Use Factories for Test Data**: Don't create users/projects manually, use factories
2. **Request Only What You Need**: If you only need a user, request `test_user`, not `test_project`
3. **Use Suffixes for Multiple Entities**: `create_test_user(conn, suffix="1")` for stable IDs
4. **Clean Up in Tests**: If you create extra data, clean it up (or rely on auto-cleanup)
5. **Use Dependency Overrides**: Never monkey patch FastAPI dependencies
6. **Keep Tests Fast**: Share session fixtures, avoid unnecessary DB writes
7. **Write Descriptive Docstrings**: Explain what fixtures are used and why
8. **Reuse DB Connections**: Always use `db_connection` fixture - don't create your own

## Common Patterns

### Test Multiple Projects

```python
@pytest.mark.integration
def test_project_isolation(db_connection, test_client):
    from tests.factories import create_test_project
    from tests.fixtures.auth import create_custom_auth_override
    from dakora_server.main import app

    # Create two projects with separate owners
    proj1_id, _, owner1_id = create_test_project(db_connection, suffix="1")
    proj2_id, _, owner2_id = create_test_project(db_connection, suffix="2")

    # Create prompt in project 1
    override = create_custom_auth_override(owner1_id, proj1_id)
    app.dependency_overrides.update(override)

    test_client.post(f"/api/projects/{proj1_id}/prompts/", json={...})

    # Verify project 2 doesn't see it
    override = create_custom_auth_override(owner2_id, proj2_id)
    app.dependency_overrides.update(override)

    response = test_client.get(f"/api/projects/{proj2_id}/prompts/")
    assert len(response.json()) == 0

    app.dependency_overrides.clear()
```

### Test Quotas

```python
@pytest.mark.integration
def test_quota_enforcement(db_connection, test_client):
    from tests.factories import create_test_project
    from dakora_server.core.database import workspace_quotas_table
    from sqlalchemy import insert
    from datetime import datetime, timedelta, timezone

    project_id, workspace_id, owner_id = create_test_project(db_connection, suffix="quota")

    # Create quota
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    db_connection.execute(
        insert(workspace_quotas_table).values(
            workspace_id=workspace_id,
            tier="free",
            tokens_used_month=99_900,
            tokens_limit_month=100_000,
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
        )
    )
    db_connection.commit()

    # Test that quota is enforced
    # ... test logic
```