"""
Test configuration and fixtures for Dakora tests

This module provides:
- Import of all fixtures from fixtures/ (database, auth, entities)
- Import of all factories from factories/ (users, workspaces, projects)
- Legacy fixtures for backward compatibility
- FastAPI test client

Usage:
    # New pattern (recommended)
    def test_api_endpoint(test_project, test_client, override_auth_dependencies):
        project_id, _, _ = test_project
        response = test_client.get(f"/api/projects/{project_id}/prompts/")
        assert response.status_code == 200

    # Create custom test data
    def test_with_multiple_projects(db_connection):
        from tests.factories import create_test_project
        proj1_id, _, _ = create_test_project(db_connection, suffix="1")
        proj2_id, _, _ = create_test_project(db_connection, suffix="2")
"""

import tempfile
import os
from pathlib import Path
import yaml
import pytest
import threading
import time
import requests
from contextlib import contextmanager

from dakora_server.config import settings
from dakora_server.core.vault import Vault

# Import all fixtures and factories for test usage
from tests.fixtures import *  # noqa: F401, F403
from tests.factories import *  # noqa: F401, F403

try:
    from dakora.playground import create_playground  # type: ignore
except Exception:
    # Fallback: create a minimal playground wrapper using the local FastAPI app
    from dakora_server.main import create_app
    import uvicorn

    class _FallbackPlayground:
        def __init__(self, host: str, port: int, vault: Vault):
            self.host = host
            self.port = port
            self.vault: Vault = vault
            self.app = create_app()

        def run(self, debug: bool = False):
            uvicorn.run(self.app, host=self.host, port=self.port, reload=debug)

    from typing import Optional

    def create_playground(
        config_path: Optional[str] = None,
        prompt_dir: Optional[str] = None,
        host: str = "127.0.0.1",
        port: int = 0,
    ) -> _FallbackPlayground:
        # Create a Vault instance and return a simple Playground-like object
        vault = Vault(registry=None, prompt_dir=prompt_dir)
        return _FallbackPlayground(host=host, port=port or 3000, vault=vault)


from typing import Generator, Any
from uuid import UUID


# ============================================================================
# LEGACY FIXTURES (for backward compatibility)
# ============================================================================
# These fixtures are maintained for existing tests that haven't been migrated
# to the new fixture system. New tests should use the fixtures from fixtures/
# ============================================================================


@pytest.fixture(scope="module")
def test_project_id(db_engine) -> Generator[str, None, None]:
    """LEGACY: Generate a test project UUID and create required database records.

    DEPRECATED: Use test_project fixture instead.
    This fixture is kept for backward compatibility with existing tests.

    Module-scoped so all tests in a module share the same project/workspace/user.
    """
    from dakora_server.core.database import get_connection
    from tests.factories import create_test_project

    with get_connection(db_engine) as conn:
        project_id, _, _ = create_test_project(conn, suffix="legacy")
        conn.commit()

    yield str(project_id)


@pytest.fixture(autouse=True)
def cleanup_prompts() -> Generator[None, None, None]:
    """LEGACY: Clean up prompts after each test.

    DEPRECATED: This is now handled by cleanup_project_data fixture.
    Kept for backward compatibility.
    """
    yield
    # Cleanup is now handled by the new cleanup_project_data fixture


@pytest.fixture
def scoped_vault_for_project(test_project_id: str):
    """Helper function to create a project-scoped vault from a base vault."""
    def _scope_vault(base_vault: Vault) -> Vault:
        """Scope a vault to a specific project."""
        from typing import cast
        from dakora_server.core.registry import Registry

        scoped_registry = cast(
            Registry,
            base_vault.registry.with_prefix(f"projects/{test_project_id}")  # type: ignore[attr-defined]
        )
        return Vault(scoped_registry, logging_enabled=False)

    return _scope_vault


@pytest.fixture(autouse=True)
def mock_settings_prompt_dir(monkeypatch: pytest.MonkeyPatch) -> Generator[Any, Any, Any]:
    """Override settings.prompt_dir to use a temporary directory for all tests.
    
    This fixture runs automatically for all tests and ensures that tests
    don't try to write to /app which may not have permissions in CI environments.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setenv("PROMPT_DIR", tmpdir)
        monkeypatch.setattr("dakora_server.config.settings.prompt_dir", tmpdir)
        # Reset the vault instance so next access creates a new one
        import dakora_server.config
        dakora_server.config._vault_instance = None  # type: ignore[attr-defined]
        try:
            yield
        finally:
            # Clean up after test
            dakora_server.config._vault_instance = None  # type: ignore[attr-defined]


@pytest.fixture
def temp_project_dir() -> Generator[tuple[str, Path], None, None]:
    """Create a temporary directory with a Dakora project setup"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create config file
        config: dict[str, object] = {
            "registry": "local",
            "prompt_dir": "./prompts",
            "logging": {"enabled": False},  # Disable logging for tests
        }

        config_path = Path(tmpdir) / "dakora.yaml"
        config_path.write_text(yaml.safe_dump(config))

        # Create prompts directory
        prompts_dir = Path(tmpdir) / "prompts"
        prompts_dir.mkdir()
        # Create test templates
        test_templates: list[dict[str, object]] = [
            {
                "id": "simple-greeting",
                "version": "1.0.0",
                "description": "A simple greeting template",
                "template": "Hello {{ name }}!",
                "inputs": {"name": {"type": "string", "required": True}},
            },
            {
                "id": "complex-template",
                "version": "2.1.0",
                "description": "A complex template with multiple inputs",
                "template": """Welcome {{ name }}!
{% if age %}You are {{ age }} years old.{% endif %}
{% if hobbies %}Your hobbies: {{ hobbies | join(", ") }}{% endif %}
{{ message | default("Have a great day!") }}""",
                "inputs": {
                    "name": {"type": "string", "required": True},
                    "age": {"type": "number", "required": False},
                    "hobbies": {"type": "array<string>", "required": False},
                    "message": {
                        "type": "string",
                        "required": False,
                        "default": "Welcome to Dakora!",
                    },
                },
                "metadata": {"category": "greeting", "tags": ["test", "complex"]},
            },
            {
                "id": "error-template",
                "version": "1.0.0",
                "description": "Template that will cause render errors",
                "template": "Hello {{ undefined_var.missing_attr }}!",
                "inputs": {"name": {"type": "string", "required": True}},
            },
        ]

        for template in test_templates:
            template_path = prompts_dir / f"{template['id']}.yaml"
            template_path.write_text(yaml.safe_dump(template))

        yield tmpdir, config_path


@pytest.fixture
def test_vault(temp_project_dir: tuple[str, Path]) -> Generator[Vault, None, None]:
    """Create a Vault instance for testing"""
    tmpdir, config_path = temp_project_dir
    original_cwd = os.getcwd()
    os.chdir(tmpdir)

    try:
        vault = Vault(str(config_path))
        yield vault
    finally:
        os.chdir(original_cwd)


@contextmanager
def playground_server(vault: Vault, port: int = 0):
    """Context manager that starts a playground server and yields the base URL"""
    # Find available port if port=0
    if port == 0:
        import socket

        sock = socket.socket()
        sock.bind(("", 0))
        port = sock.getsockname()[1]
        sock.close()

    playground = create_playground(
        config_path=None,
        prompt_dir=vault.config["prompt_dir"],
        host="127.0.0.1",
        port=port,
    )

    # Start server in thread
    server_thread = threading.Thread(
        target=lambda: playground.run(debug=False), daemon=True
    )
    server_thread.start()

    # Wait for server to start
    base_url = f"http://127.0.0.1:{port}"
    max_attempts = 30
    for _ in range(max_attempts):
        try:
            response = requests.get(f"{base_url}/api/health", timeout=1)
            if response.status_code == 200:
                break
        except (requests.exceptions.RequestException, requests.exceptions.Timeout):
            time.sleep(0.1)
    else:
        raise RuntimeError("Playground server failed to start")

    try:
        yield base_url
    finally:
        # Server will be stopped when thread exits
        pass


@pytest.fixture
def playground_url(test_vault: Vault) -> Generator[str, None, None]:
    """Fixture that provides a running playground server URL"""
    with playground_server(test_vault) as url:
        yield url


# API Key test fixtures
@pytest.fixture
def test_user_id(test_user: UUID) -> UUID:
    """LEGACY: Get the test user ID.

    DEPRECATED: Use test_user fixture directly.
    Kept for backward compatibility.
    """
    return test_user


@pytest.fixture
def clean_api_keys() -> Generator[None, None, None]:
    """LEGACY: Clean up API keys after each test.

    DEPRECATED: This is now handled by cleanup_project_data fixture.
    Kept for backward compatibility.
    """
    yield
    # Cleanup is now handled by the new cleanup_project_data fixture


# Execution API test fixtures
@pytest.fixture
def test_engine(db_engine):
    """LEGACY: Create a database engine for tests.

    DEPRECATED: Use db_engine fixture directly.
    Kept for backward compatibility.
    """
    return db_engine


@pytest.fixture
def test_client():
    """Create a FastAPI test client.

    Use with override_auth_dependencies to test authenticated endpoints:

    Example:
        def test_endpoint(test_client, override_auth_dependencies):
            response = test_client.get("/api/...")
            assert response.status_code == 200
    """
    from fastapi.testclient import TestClient
    from dakora_server.main import app

    original_auth_required = settings.auth_required
    settings.auth_required = True

    client = TestClient(app)
    try:
        yield client
    finally:
        client.close()
        settings.auth_required = original_auth_required


@pytest.fixture
def setup_test_data(db_engine):
    """LEGACY: Create user, workspace, project with quota for testing.

    DEPRECATED: Use test_project fixture with custom quota setup instead.
    Kept for backward compatibility with quota tests.
    """
    from dakora_server.core.database import (
        get_connection,
        workspace_quotas_table,
    )
    from sqlalchemy import insert, delete
    from datetime import datetime, timedelta, timezone
    from tests.factories import create_test_project

    with get_connection(db_engine) as conn:
        project_id, workspace_id, user_id = create_test_project(conn, suffix="quota")

        # Create quota
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        conn.execute(
            insert(workspace_quotas_table).values(
                workspace_id=workspace_id,
                tier="free",
                tokens_used_month=0,
                current_period_start=now,
                current_period_end=now + timedelta(days=30),
            )
        )
        conn.commit()

    yield str(user_id), str(workspace_id), str(project_id)

    # Cleanup
    with get_connection(db_engine) as conn:
        from dakora_server.core.database import (
            projects_table,
            workspaces_table,
            workspace_members_table,
            users_table,
        )
        conn.execute(delete(workspace_quotas_table).where(
            workspace_quotas_table.c.workspace_id == workspace_id
        ))
        conn.execute(delete(projects_table).where(projects_table.c.id == project_id))
        conn.execute(delete(workspace_members_table).where(
            workspace_members_table.c.workspace_id == workspace_id
        ))
        conn.execute(delete(workspaces_table).where(workspaces_table.c.id == workspace_id))
        conn.execute(delete(users_table).where(users_table.c.id == user_id))
        conn.commit()


@pytest.fixture
def mock_provider():
    """Create a mock LLM provider for testing."""
    from unittest.mock import MagicMock

    provider = MagicMock()
    return provider


@pytest.fixture
def auth_override(setup_test_data):
    """LEGACY: Override authentication for tests.

    DEPRECATED: Use override_auth_dependencies fixture instead.
    Kept for backward compatibility with existing tests.
    """
    from dakora_server.auth import validate_project_access, get_auth_context, get_current_user_id, AuthContext
    from dakora_server.main import app

    user_id, workspace_id, project_id = setup_test_data

    # Override get_auth_context to return test auth context
    async def mock_get_auth_context():
        return AuthContext(user_id=user_id, project_id=None, auth_method="test")

    # Override validate_project_access to return the project UUID directly
    async def mock_validate_project_access():
        return UUID(project_id)

    # Override get_current_user_id to return the user UUID directly
    async def mock_get_current_user_id():
        return UUID(user_id)

    app.dependency_overrides[get_auth_context] = mock_get_auth_context
    app.dependency_overrides[validate_project_access] = mock_validate_project_access
    app.dependency_overrides[get_current_user_id] = mock_get_current_user_id
    yield
    app.dependency_overrides.clear()
