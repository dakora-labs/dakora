"""Tests for prompt versioning functionality."""

import pytest
from uuid import uuid4
from sqlalchemy import select, delete

from dakora_server.core.prompt_manager import PromptManager
from dakora_server.core.model import TemplateSpec
from dakora_server.core.database import (
    prompts_table,
    prompt_versions_table,
    get_connection,
)
from dakora_server.core.exceptions import TemplateNotFound
from tests.factories.users import create_test_user
from tests.factories.workspaces import create_test_workspace
from tests.factories.projects import create_test_project


@pytest.fixture
def test_prompt_data():
    """Test data factory for prompts."""
    return {
        "id": "test-prompt",
        "version": "1.0.0",
        "description": "Test prompt",
        "template": "Hello {{name}}!",
        "inputs": {
            "name": {
                "type": "string",
                "description": "User name",
            }
        },
    }


@pytest.fixture(autouse=True)
def cleanup_test_prompts(db_connection):
    """Clean up test prompts after each test."""
    yield

    # Rollback any failed transactions
    db_connection.rollback()

    # Clean up test data
    db_connection.execute(
        delete(prompts_table).where(
            prompts_table.c.prompt_id.like("test-prompt%")
        )
    )
    db_connection.commit()


@pytest.mark.integration
class TestPromptVersioning:
    """Tests for automatic prompt versioning."""

    def test_new_prompt_creates_version_1(
        self, prompt_manager, test_prompt_data, db_connection, test_user
    ):
        """Test that creating a new prompt creates version 1."""
        spec = TemplateSpec.model_validate(test_prompt_data)

        # Save new prompt
        prompt_manager.save(spec, user_id=test_user)

        # Check database
        with get_connection(prompt_manager.engine) as conn:
            # Verify prompts table
            prompt = conn.execute(
                select(
                    prompts_table.c.version_number,
                    prompts_table.c.content_hash,
                    prompts_table.c.storage_path,
                )
                .where(prompts_table.c.prompt_id == spec.id)
            ).fetchone()

            assert prompt is not None
            assert prompt[0] == 1  # version_number
            assert prompt[1] is not None  # content_hash
            assert "_v1.yaml" in prompt[2]  # storage_path

            # Verify version history
            # Need to get the prompt UUID first to query versions
            prompt_uuid = conn.execute(
                select(prompts_table.c.id)
                .where(prompts_table.c.prompt_id == spec.id)
            ).scalar()
            
            version = conn.execute(
                select(prompt_versions_table.c.version_number, prompt_versions_table.c.created_by)
                .where(prompt_versions_table.c.prompt_id == prompt_uuid)
                .where(prompt_versions_table.c.version_number == 1)
            ).fetchone()

            assert version is not None
            assert version[0] == 1
            assert version[1] == test_user

    def test_unchanged_content_is_idempotent(
        self, prompt_manager, test_prompt_data, test_user
    ):
        """Test that saving identical content doesn't create a new version."""
        spec = TemplateSpec.model_validate(test_prompt_data)

        # Save twice
        prompt_manager.save(spec, user_id=test_user)
        prompt_manager.save(spec, user_id=test_user)

        # Should still be version 1
        with get_connection(prompt_manager.engine) as conn:
            prompt = conn.execute(
                select(prompts_table.c.version_number)
                .where(prompts_table.c.prompt_id == spec.id)
            ).fetchone()

            assert prompt[0] == 1

            # Should only have one version entry
            versions = conn.execute(
                select(prompt_versions_table)
                .join(
                    prompts_table,
                    prompt_versions_table.c.prompt_id == prompts_table.c.id,
                )
                .where(prompts_table.c.prompt_id == spec.id)
            ).fetchall()

            assert len(versions) == 1

    def test_content_change_creates_new_version(
        self, prompt_manager, test_prompt_data, test_user
    ):
        """Test that changing content creates a new version."""
        spec = TemplateSpec.model_validate(test_prompt_data)

        # Save initial version
        prompt_manager.save(spec, user_id=test_user)

        # Modify content
        spec.template = "Goodbye {{name}}!"
        prompt_manager.save(spec, user_id=test_user)

        # Should be version 2
        with get_connection(prompt_manager.engine) as conn:
            prompt = conn.execute(
                select(prompts_table.c.version_number, prompts_table.c.storage_path)
                .where(prompts_table.c.prompt_id == spec.id)
            ).fetchone()

            assert prompt[0] == 2
            assert "_v2.yaml" in prompt[1]

            # Should have two version entries
            versions = conn.execute(
                select(prompt_versions_table.c.version_number)
                .join(
                    prompts_table,
                    prompt_versions_table.c.prompt_id == prompts_table.c.id,
                )
                .where(prompts_table.c.prompt_id == spec.id)
                .order_by(prompt_versions_table.c.version_number)
            ).fetchall()

            assert len(versions) == 2
            assert versions[0][0] == 1
            assert versions[1][0] == 2

    def test_get_version_history(self, prompt_manager, test_prompt_data, test_user):
        """Test retrieving version history."""
        spec = TemplateSpec.model_validate(test_prompt_data)

        # Create multiple versions
        prompt_manager.save(spec, user_id=test_user)

        spec.template = "Version 2"
        prompt_manager.save(spec, user_id=test_user)

        spec.template = "Version 3"
        prompt_manager.save(spec, user_id=test_user)

        # Get history
        history = prompt_manager.get_version_history(spec.id)

        assert len(history) == 3
        # Should be ordered newest first
        assert history[0]["version"] == 3
        assert history[1]["version"] == 2
        assert history[2]["version"] == 1

        # Check metadata
        for version_info in history:
            assert "content_hash" in version_info
            assert "created_at" in version_info
            assert "created_by" in version_info
            assert "storage_path" in version_info
            assert "metadata" in version_info

    def test_get_version_content(self, prompt_manager, test_prompt_data, test_user):
        """Test loading a specific version."""
        spec = TemplateSpec.model_validate(test_prompt_data)

        # Create versions
        prompt_manager.save(spec, user_id=test_user)

        spec.template = "Version 2 content"
        prompt_manager.save(spec, user_id=test_user)

        # Load version 1
        v1_spec = prompt_manager.get_version_content(spec.id, 1)
        assert v1_spec.template == "Hello {{name}}!"

        # Load version 2
        v2_spec = prompt_manager.get_version_content(spec.id, 2)
        assert v2_spec.template == "Version 2 content"

    def test_rollback_to_previous_version(
        self, prompt_manager, test_prompt_data, test_user
    ):
        """Test rolling back to a previous version."""
        spec = TemplateSpec.model_validate(test_prompt_data)

        # Create versions
        prompt_manager.save(spec, user_id=test_user)

        spec.template = "Version 2"
        prompt_manager.save(spec, user_id=test_user)

        spec.template = "Version 3"
        prompt_manager.save(spec, user_id=test_user)

        # Rollback to version 1
        restored_spec = prompt_manager.rollback_to_version(
            spec.id, 1, user_id=test_user
        )

        # Should create version 4 with content from version 1
        with get_connection(prompt_manager.engine) as conn:
            prompt = conn.execute(
                select(prompts_table.c.version_number)
                .where(prompts_table.c.prompt_id == spec.id)
            ).fetchone()

            assert prompt[0] == 4

        # Content should match version 1
        assert restored_spec.template == "Hello {{name}}!"

        # Version history should have 4 entries
        history = prompt_manager.get_version_history(spec.id)
        assert len(history) == 4

    def test_version_not_found(self, prompt_manager, test_prompt_data, test_user):
        """Test error handling for non-existent versions."""
        spec = TemplateSpec.model_validate(test_prompt_data)
        prompt_manager.save(spec, user_id=test_user)

        # Try to get non-existent version
        with pytest.raises(TemplateNotFound):
            prompt_manager.get_version_content(spec.id, 99)

        # Try to rollback to non-existent version
        with pytest.raises(TemplateNotFound):
            prompt_manager.rollback_to_version(spec.id, 99, user_id=test_user)

    def test_content_hash_normalization(
        self, prompt_manager, test_prompt_data, test_user
    ):
        """Test that content hash normalization prevents false positives."""
        spec = TemplateSpec.model_validate(test_prompt_data)

        # Save initial version
        prompt_manager.save(spec, user_id=test_user)

        # Get initial hash
        with get_connection(prompt_manager.engine) as conn:
            initial_hash = conn.execute(
                select(prompts_table.c.content_hash)
                .where(prompts_table.c.prompt_id == spec.id)
            ).fetchone()[0]

        # Save again with identical content (should be idempotent)
        prompt_manager.save(spec, user_id=test_user)

        # Hash should be unchanged and still version 1
        with get_connection(prompt_manager.engine) as conn:
            result = conn.execute(
                select(prompts_table.c.version_number, prompts_table.c.content_hash)
                .where(prompts_table.c.prompt_id == spec.id)
            ).fetchone()

            assert result[0] == 1
            assert result[1] == initial_hash


@pytest.fixture
def prompt_manager(db_connection, test_project, storage_backend):
    """Create a PromptManager instance for testing."""
    from dakora_server.core.registry import TemplateRegistry

    project_id, _, _ = test_project

    registry = TemplateRegistry(
        storage_backend, prefix=f"projects/{project_id}"
    )

    manager = PromptManager(
        registry=registry,
        engine=db_connection.engine,
        project_id=project_id,
    )

    return manager


@pytest.fixture
def test_user(db_connection):
    """Create a test user."""
    user_id = create_test_user(db_connection, clerk_user_id="test_versioning_user")
    db_connection.commit()
    return user_id


@pytest.fixture
def test_workspace(db_connection, test_user):
    """Create a test workspace."""
    workspace_id, owner_id = create_test_workspace(
        db_connection,
        owner_id=test_user,
        slug="test-versioning-workspace",
    )
    db_connection.commit()
    return workspace_id, owner_id


@pytest.fixture
def test_project(db_connection, test_workspace):
    """Create a test project."""
    workspace_id, owner_id = test_workspace
    project_id, _, _ = create_test_project(
        db_connection,
        workspace_id=workspace_id,
        slug="test-versioning-project",
    )
    db_connection.commit()
    return project_id, workspace_id, owner_id


@pytest.fixture
def storage_backend(tmp_path):
    """Create a local storage backend for testing."""
    from dakora_server.core.registry.backends import LocalFSBackend

    # Ensure the directory exists
    tmp_path.mkdir(parents=True, exist_ok=True)
    return LocalFSBackend(root=str(tmp_path))