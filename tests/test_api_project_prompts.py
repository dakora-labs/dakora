"""Tests for project-scoped prompts API routes."""

import pytest
import os
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy import insert, text
from dakora_server.main import create_app
from dakora_server.core.database import (
    create_test_engine,
    get_connection,
    users_table,
    workspaces_table,
    workspace_members_table,
    projects_table,
    prompts_table,
)


@pytest.fixture
def test_db_url():
    """Get test database URL from environment or use default."""
    return os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/dakora"
    )


@pytest.fixture
def test_engine(test_db_url):
    """Create test database engine."""
    engine = create_test_engine(test_db_url)

    # Ensure database is available
    try:
        with get_connection(engine) as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        pytest.skip("Database not available")

    yield engine
    engine.dispose()


@pytest.fixture
def test_project(test_engine):
    """Create test user, workspace, and project."""
    with get_connection(test_engine) as conn:
        # Create user
        user_result = conn.execute(
            insert(users_table).values(
                clerk_user_id="test_user_123",
                email="test@example.com",
                name="Test User",
            ).returning(users_table.c.id)
        )
        user_id = user_result.fetchone()[0]

        # Create workspace
        workspace_result = conn.execute(
            insert(workspaces_table).values(
                slug="test-workspace",
                name="Test Workspace",
                type="personal",
                owner_id=user_id,
            ).returning(workspaces_table.c.id)
        )
        workspace_id = workspace_result.fetchone()[0]

        # Create workspace membership
        conn.execute(
            insert(workspace_members_table).values(
                workspace_id=workspace_id,
                user_id=user_id,
                role="owner",
            )
        )

        # Create project
        project_result = conn.execute(
            insert(projects_table).values(
                workspace_id=workspace_id,
                slug="default",
                name="Default Project",
                description="Test project",
            ).returning(projects_table.c.id)
        )
        project_id = project_result.fetchone()[0]

        conn.commit()

        yield {
            "user_id": user_id,
            "workspace_id": workspace_id,
            "project_id": project_id,
        }

        # Cleanup (cascade deletes will handle most of it)
        conn.execute(users_table.delete().where(users_table.c.id == user_id))
        conn.commit()


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


class TestListPrompts:
    """Tests for GET /api/projects/{project_id}/prompts"""

    def test_list_empty_project(self, client, test_project):
        """Test listing prompts in empty project."""
        project_id = test_project["project_id"]
        response = client.get(f"/api/projects/{project_id}/prompts")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_with_prompts(self, client, test_project, test_engine):
        """Test listing prompts with data."""
        project_id = test_project["project_id"]

        # Create prompts in database
        with get_connection(test_engine) as conn:
            conn.execute(
                insert(prompts_table).values(
                    project_id=project_id,
                    prompt_id="prompt1",
                    version="1.0.0",
                    description="First prompt",
                    storage_path=f"projects/{project_id}/prompt1.yaml",
                )
            )
            conn.execute(
                insert(prompts_table).values(
                    project_id=project_id,
                    prompt_id="prompt2",
                    version="1.0.0",
                    description="Second prompt",
                    storage_path=f"projects/{project_id}/prompt2.yaml",
                )
            )
            conn.commit()

        response = client.get(f"/api/projects/{project_id}/prompts")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert set(data) == {"prompt1", "prompt2"}

    def test_list_nonexistent_project(self, client):
        """Test listing prompts for non-existent project."""
        fake_project_id = uuid4()
        response = client.get(f"/api/projects/{fake_project_id}/prompts")
        assert response.status_code == 404


class TestCreatePrompt:
    """Tests for POST /api/projects/{project_id}/prompts"""

    def test_create_prompt_success(self, client, test_project):
        """Test creating a new prompt."""
        project_id = test_project["project_id"]

        payload = {
            "id": "new_prompt",
            "version": "1.0.0",
            "description": "A new prompt",
            "template": "Hello {{ name }}!",
            "inputs": {
                "name": {"type": "string", "required": True}
            },
            "metadata": {"tags": ["test"]},
        }

        response = client.post(f"/api/projects/{project_id}/prompts", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == "new_prompt"
        assert data["version"] == "1.0.0"
        assert data["description"] == "A new prompt"

    def test_create_prompt_duplicate(self, client, test_project, test_engine):
        """Test creating duplicate prompt fails."""
        project_id = test_project["project_id"]

        # Create first prompt
        payload = {
            "id": "duplicate_prompt",
            "version": "1.0.0",
            "template": "Test",
            "inputs": {},
        }
        response = client.post(f"/api/projects/{project_id}/prompts", json=payload)
        assert response.status_code == 201

        # Try to create again
        response = client.post(f"/api/projects/{project_id}/prompts", json=payload)
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_create_prompt_empty_id(self, client, test_project):
        """Test creating prompt with empty ID fails."""
        project_id = test_project["project_id"]

        payload = {
            "id": "",
            "version": "1.0.0",
            "template": "Test",
            "inputs": {},
        }

        response = client.post(f"/api/projects/{project_id}/prompts", json=payload)
        assert response.status_code == 422


class TestGetPrompt:
    """Tests for GET /api/projects/{project_id}/prompts/{prompt_id}"""

    def test_get_existing_prompt(self, client, test_project):
        """Test getting an existing prompt."""
        project_id = test_project["project_id"]

        # Create prompt
        payload = {
            "id": "test_prompt",
            "version": "1.0.0",
            "description": "Test",
            "template": "Hello!",
            "inputs": {},
        }
        client.post(f"/api/projects/{project_id}/prompts", json=payload)

        # Get prompt
        response = client.get(f"/api/projects/{project_id}/prompts/test_prompt")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test_prompt"
        assert data["version"] == "1.0.0"

    def test_get_nonexistent_prompt(self, client, test_project):
        """Test getting non-existent prompt."""
        project_id = test_project["project_id"]
        response = client.get(f"/api/projects/{project_id}/prompts/nonexistent")
        assert response.status_code == 404


class TestUpdatePrompt:
    """Tests for PUT /api/projects/{project_id}/prompts/{prompt_id}"""

    def test_update_prompt_success(self, client, test_project):
        """Test updating an existing prompt."""
        project_id = test_project["project_id"]

        # Create prompt
        payload = {
            "id": "test_prompt",
            "version": "1.0.0",
            "template": "Hello!",
            "inputs": {},
        }
        client.post(f"/api/projects/{project_id}/prompts", json=payload)

        # Update prompt
        update_payload = {
            "version": "2.0.0",
            "template": "Hi!",
        }
        response = client.put(
            f"/api/projects/{project_id}/prompts/test_prompt", json=update_payload
        )
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "2.0.0"
        assert data["template"] == "Hi!"

    def test_update_nonexistent_prompt(self, client, test_project):
        """Test updating non-existent prompt."""
        project_id = test_project["project_id"]

        update_payload = {"version": "2.0.0"}
        response = client.put(
            f"/api/projects/{project_id}/prompts/nonexistent", json=update_payload
        )
        assert response.status_code == 404


class TestDeletePrompt:
    """Tests for DELETE /api/projects/{project_id}/prompts/{prompt_id}"""

    def test_delete_prompt_success(self, client, test_project, test_engine):
        """Test deleting an existing prompt."""
        project_id = test_project["project_id"]

        # Create prompt
        payload = {
            "id": "test_prompt",
            "version": "1.0.0",
            "template": "Hello!",
            "inputs": {},
        }
        client.post(f"/api/projects/{project_id}/prompts", json=payload)

        # Delete prompt
        response = client.delete(f"/api/projects/{project_id}/prompts/test_prompt")
        assert response.status_code == 204

        # Verify deleted
        response = client.get(f"/api/projects/{project_id}/prompts/test_prompt")
        assert response.status_code == 404

    def test_delete_nonexistent_prompt(self, client, test_project):
        """Test deleting non-existent prompt."""
        project_id = test_project["project_id"]
        response = client.delete(f"/api/projects/{project_id}/prompts/nonexistent")
        assert response.status_code == 404