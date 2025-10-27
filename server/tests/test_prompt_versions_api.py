"""Unit tests for prompt version API endpoints"""

import pytest
from unittest.mock import MagicMock
from datetime import datetime
from uuid import uuid4

from dakora_server.core.model import TemplateSpec, InputSpec
from dakora_server.core.exceptions import TemplateNotFound


@pytest.fixture
def mock_prompt_manager():
    """Create a mock PromptManager for testing."""
    return MagicMock()


@pytest.fixture
def sample_spec():
    """Create a sample TemplateSpec for testing."""
    return TemplateSpec(
        id="test-prompt",
        version="1.0.0",
        description="Test prompt",
        template="Hello {{ name }}!",
        inputs={"name": InputSpec(type="string", required=True)},
        metadata={"tags": ["test"]},
    )


def test_get_version_history_success(test_client, mock_prompt_manager, override_auth_dependencies):
    """Test getting version history returns list of versions."""
    from dakora_server.api.project_prompts import get_prompt_manager
    from dakora_server.main import app

    project_id = str(uuid4())
    prompt_id = "test-prompt"
    user_id = uuid4()

    # Mock version history data
    mock_versions = [
        {
            "version": 1,
            "content_hash": "abc123",
            "created_at": datetime(2024, 1, 1, 12, 0, 0),
            "created_by": user_id,
            "metadata": {},
        },
        {
            "version": 2,
            "content_hash": "def456",
            "created_at": datetime(2024, 1, 2, 12, 0, 0),
            "created_by": user_id,
            "metadata": {"note": "Fixed typo"},
        },
    ]
    mock_prompt_manager.get_version_history.return_value = mock_versions

    app.dependency_overrides[get_prompt_manager] = lambda: mock_prompt_manager

    try:
        response = test_client.get(f"/api/projects/{project_id}/prompts/{prompt_id}/versions")

        assert response.status_code == 200
        data = response.json()
        assert "versions" in data
        assert len(data["versions"]) == 2
        assert data["versions"][0]["version"] == 1
        assert data["versions"][0]["content_hash"] == "abc123"
        assert data["versions"][1]["version"] == 2
        assert data["versions"][1]["metadata"]["note"] == "Fixed typo"
    finally:
        app.dependency_overrides.pop(get_prompt_manager, None)


def test_get_version_history_not_found(test_client, mock_prompt_manager, override_auth_dependencies):
    """Test getting version history for non-existent prompt returns 404."""
    from dakora_server.api.project_prompts import get_prompt_manager
    from dakora_server.main import app

    project_id = str(uuid4())
    prompt_id = "nonexistent"

    mock_prompt_manager.get_version_history.side_effect = TemplateNotFound(prompt_id)

    app.dependency_overrides[get_prompt_manager] = lambda: mock_prompt_manager

    try:
        response = test_client.get(f"/api/projects/{project_id}/prompts/{prompt_id}/versions")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    finally:
        app.dependency_overrides.pop(get_prompt_manager, None)


def test_get_version_content_success(test_client, mock_prompt_manager, sample_spec, override_auth_dependencies):
    """Test getting specific version content returns full prompt spec."""
    from dakora_server.api.project_prompts import get_prompt_manager
    from dakora_server.main import app

    project_id = str(uuid4())
    prompt_id = "test-prompt"
    version = 2

    mock_prompt_manager.get_version_content.return_value = sample_spec

    app.dependency_overrides[get_prompt_manager] = lambda: mock_prompt_manager

    try:
        response = test_client.get(f"/api/projects/{project_id}/prompts/{prompt_id}/versions/{version}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test-prompt"
        assert data["version"] == "1.0.0"
        assert data["description"] == "Test prompt"
        assert data["template"] == "Hello {{ name }}!"
        assert "name" in data["inputs"]
        assert data["metadata"]["tags"] == ["test"]
    finally:
        app.dependency_overrides.pop(get_prompt_manager, None)


def test_get_version_content_not_found(test_client, mock_prompt_manager, override_auth_dependencies):
    """Test getting non-existent version returns 404."""
    from dakora_server.api.project_prompts import get_prompt_manager
    from dakora_server.main import app

    project_id = str(uuid4())
    prompt_id = "test-prompt"
    version = 99

    mock_prompt_manager.get_version_content.side_effect = TemplateNotFound(prompt_id)

    app.dependency_overrides[get_prompt_manager] = lambda: mock_prompt_manager

    try:
        response = test_client.get(f"/api/projects/{project_id}/prompts/{prompt_id}/versions/{version}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    finally:
        app.dependency_overrides.pop(get_prompt_manager, None)


def test_rollback_prompt_success(test_client, mock_prompt_manager, sample_spec, override_auth_dependencies):
    """Test rolling back to previous version creates new version."""
    from dakora_server.api.project_prompts import get_prompt_manager
    from dakora_server.main import app

    project_id = str(uuid4())
    prompt_id = "test-prompt"
    target_version = 2

    # Create updated spec with new version number
    rolled_back_spec = TemplateSpec(
        id=sample_spec.id,
        version="1.0.0",
        description=sample_spec.description,
        template=sample_spec.template,
        inputs=sample_spec.inputs,
        metadata=sample_spec.metadata,
    )

    mock_prompt_manager.rollback_to_version.return_value = rolled_back_spec

    app.dependency_overrides[get_prompt_manager] = lambda: mock_prompt_manager

    try:
        response = test_client.post(
            f"/api/projects/{project_id}/prompts/{prompt_id}/rollback",
            json={"version": target_version}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test-prompt"
        assert data["template"] == "Hello {{ name }}!"
        mock_prompt_manager.rollback_to_version.assert_called_once_with(prompt_id, target_version)
    finally:
        app.dependency_overrides.pop(get_prompt_manager, None)


def test_rollback_prompt_not_found(test_client, mock_prompt_manager, override_auth_dependencies):
    """Test rollback to non-existent prompt/version returns 404."""
    from dakora_server.api.project_prompts import get_prompt_manager
    from dakora_server.main import app

    project_id = str(uuid4())
    prompt_id = "test-prompt"
    target_version = 99

    mock_prompt_manager.rollback_to_version.side_effect = TemplateNotFound(prompt_id)

    app.dependency_overrides[get_prompt_manager] = lambda: mock_prompt_manager

    try:
        response = test_client.post(
            f"/api/projects/{project_id}/prompts/{prompt_id}/rollback",
            json={"version": target_version}
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    finally:
        app.dependency_overrides.pop(get_prompt_manager, None)


def test_rollback_prompt_invalid_version(test_client, mock_prompt_manager, override_auth_dependencies):
    """Test rollback with invalid version number returns 400."""
    from dakora_server.api.project_prompts import get_prompt_manager
    from dakora_server.main import app

    project_id = str(uuid4())
    prompt_id = "test-prompt"
    target_version = 2

    mock_prompt_manager.rollback_to_version.side_effect = ValueError("Invalid version")

    app.dependency_overrides[get_prompt_manager] = lambda: mock_prompt_manager

    try:
        response = test_client.post(
            f"/api/projects/{project_id}/prompts/{prompt_id}/rollback",
            json={"version": target_version}
        )

        assert response.status_code == 400
        assert "Invalid version" in response.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_prompt_manager, None)


def test_rollback_prompt_validation_error(test_client, override_auth_dependencies):
    """Test rollback with invalid request body returns 422."""
    from dakora_server.main import app

    project_id = str(uuid4())
    prompt_id = "test-prompt"

    # Invalid version (must be positive integer)
    response = test_client.post(
        f"/api/projects/{project_id}/prompts/{prompt_id}/rollback",
        json={"version": 0}
    )

    assert response.status_code == 422