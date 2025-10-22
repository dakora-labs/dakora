"""Tests for PromptManager - database + blob storage integration."""

import pytest
import os
from uuid import uuid4
from sqlalchemy import text
from dakora_server.core.prompt_manager import PromptManager
from dakora_server.core.model import TemplateSpec, InputSpec
from dakora_server.core.registry import LocalRegistry
from dakora_server.core.database import create_test_engine, prompts_table, get_connection, metadata
from dakora_server.core.exceptions import TemplateNotFound


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

    # Ensure tables exist
    try:
        with get_connection(engine) as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        pytest.skip("Database not available")

    yield engine
    engine.dispose()


@pytest.fixture
def test_registry(tmp_path):
    """Create test registry with temp directory."""
    registry_dir = tmp_path / "prompts"
    registry_dir.mkdir()
    return LocalRegistry(str(registry_dir))


@pytest.fixture
def project_id(test_engine):
    """Create a test project and return its UUID."""
    from sqlalchemy import insert
    from dakora_server.core.database import users_table, workspaces_table, projects_table

    with get_connection(test_engine) as conn:
        # Create test user
        user_result = conn.execute(
            insert(users_table).values(
                clerk_user_id=f"test_pm_{uuid4()}",
                email=f"test_pm_{uuid4()}@example.com",
                name="Test User",
            ).returning(users_table.c.id)
        )
        user_id = user_result.fetchone()[0]

        # Create test workspace
        workspace_result = conn.execute(
            insert(workspaces_table).values(
                slug=f"test-pm-{uuid4()}",
                name="Test Workspace",
                type="personal",
                owner_id=user_id,
            ).returning(workspaces_table.c.id)
        )
        workspace_id = workspace_result.fetchone()[0]

        # Create test project
        project_result = conn.execute(
            insert(projects_table).values(
                workspace_id=workspace_id,
                slug="test-project",
                name="Test Project",
            ).returning(projects_table.c.id)
        )
        project_id = project_result.fetchone()[0]

        conn.commit()

        yield project_id

        # Cleanup (cascade will handle workspace/project)
        conn.execute(users_table.delete().where(users_table.c.id == user_id))
        conn.commit()


@pytest.fixture
def prompt_manager(test_registry, test_engine, project_id):
    """Create PromptManager instance."""
    manager = PromptManager(test_registry, test_engine, project_id)

    yield manager

    # Cleanup: delete any prompts created during test
    with get_connection(test_engine) as conn:
        conn.execute(prompts_table.delete().where(prompts_table.c.project_id == project_id))
        conn.commit()


class TestPromptManagerSave:
    """Tests for PromptManager.save()"""

    def test_save_creates_db_record(self, prompt_manager, test_engine, project_id):
        """Test that save() creates database record."""
        spec = TemplateSpec(
            id="test_prompt",
            version="1.0.0",
            description="Test prompt",
            template="Hello {{ name }}!",
            inputs={"name": InputSpec(type="string")},
        )

        prompt_manager.save(spec)

        # Check database
        with get_connection(test_engine) as conn:
            result = conn.execute(
                prompts_table.select().where(
                    prompts_table.c.project_id == project_id,
                    prompts_table.c.prompt_id == "test_prompt",
                )
            ).fetchone()

            assert result is not None
            assert result.prompt_id == "test_prompt"
            assert result.version == "1.0.0"
            assert result.description == "Test prompt"
            assert result.storage_path == f"projects/{project_id}/test_prompt.yaml"

    def test_save_updates_existing_record(self, prompt_manager, test_engine, project_id):
        """Test that save() updates existing database record."""
        # Create initial version
        spec_v1 = TemplateSpec(
            id="test_prompt",
            version="1.0.0",
            description="Version 1",
            template="Hello {{ name }}!",
            inputs={"name": InputSpec(type="string")},
        )
        prompt_manager.save(spec_v1)

        # Update to version 2
        spec_v2 = TemplateSpec(
            id="test_prompt",
            version="2.0.0",
            description="Version 2",
            template="Hi {{ name }}!",
            inputs={"name": InputSpec(type="string")},
        )
        prompt_manager.save(spec_v2)

        # Check database has only one record with updated values
        with get_connection(test_engine) as conn:
            results = conn.execute(
                prompts_table.select().where(
                    prompts_table.c.project_id == project_id,
                    prompts_table.c.prompt_id == "test_prompt",
                )
            ).fetchall()

            assert len(results) == 1
            assert results[0].version == "2.0.0"
            assert results[0].description == "Version 2"


class TestPromptManagerLoad:
    """Tests for PromptManager.load()"""

    def test_load_existing_prompt(self, prompt_manager):
        """Test loading an existing prompt."""
        spec = TemplateSpec(
            id="test_prompt",
            version="1.0.0",
            description="Test",
            template="Hello!",
        )
        prompt_manager.save(spec)

        loaded = prompt_manager.load("test_prompt")
        assert loaded.id == "test_prompt"
        assert loaded.version == "1.0.0"

    def test_load_nonexistent_prompt(self, prompt_manager):
        """Test loading non-existent prompt raises error."""
        with pytest.raises(TemplateNotFound):
            prompt_manager.load("nonexistent")


class TestPromptManagerList:
    """Tests for PromptManager.list_ids()"""

    def test_list_empty(self, prompt_manager):
        """Test listing when no prompts exist."""
        assert prompt_manager.list_ids() == []

    def test_list_multiple_prompts(self, prompt_manager):
        """Test listing multiple prompts."""
        for i in range(3):
            spec = TemplateSpec(
                id=f"prompt{i}",
                version="1.0.0",
                template=f"Template {i}",
            )
            prompt_manager.save(spec)

        ids = prompt_manager.list_ids()
        assert len(ids) == 3
        assert set(ids) == {"prompt0", "prompt1", "prompt2"}


class TestPromptManagerDelete:
    """Tests for PromptManager.delete()"""

    def test_delete_existing_prompt(self, prompt_manager, test_engine, project_id):
        """Test deleting an existing prompt."""
        spec = TemplateSpec(
            id="test_prompt",
            version="1.0.0",
            template="Hello!",
        )
        prompt_manager.save(spec)

        prompt_manager.delete("test_prompt")

        # Check database
        with get_connection(test_engine) as conn:
            result = conn.execute(
                prompts_table.select().where(
                    prompts_table.c.project_id == project_id,
                    prompts_table.c.prompt_id == "test_prompt",
                )
            ).fetchone()
            assert result is None

    def test_delete_nonexistent_prompt(self, prompt_manager):
        """Test deleting non-existent prompt raises error."""
        with pytest.raises(TemplateNotFound):
            prompt_manager.delete("nonexistent")


class TestPromptManagerSync:
    """Tests for PromptManager.sync_from_storage()"""

    def test_sync_adds_missing_records(
        self, prompt_manager, test_registry, test_engine, project_id
    ):
        """Test sync adds prompts that exist in storage but not in DB."""
        # Create prompt directly in storage (bypassing PromptManager)
        spec = TemplateSpec(
            id="orphan_prompt",
            version="1.0.0",
            template="Orphan template",
        )
        test_registry.save(spec)

        # Sync should find it and add to database
        synced_count = prompt_manager.sync_from_storage()
        assert synced_count == 1

        # Check database
        with get_connection(test_engine) as conn:
            result = conn.execute(
                prompts_table.select().where(
                    prompts_table.c.project_id == project_id,
                    prompts_table.c.prompt_id == "orphan_prompt",
                )
            ).fetchone()
            assert result is not None
            assert result.prompt_id == "orphan_prompt"