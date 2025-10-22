"""Tests for workspace and project auto-provisioning logic."""

import pytest
import os
from uuid import UUID, uuid4
from sqlalchemy import text, select

from dakora_server.core.provisioning import (
    generate_slug,
    get_first_name,
    provision_workspace_and_project,
    get_or_create_workspace,
)
from dakora_server.core.database import (
    create_test_engine,
    get_connection,
    metadata,
    users_table,
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
    """Create test engine with NullPool for testing."""
    engine = create_test_engine(test_db_url)
    yield engine
    engine.dispose()


@pytest.fixture
def setup_tables(test_engine):
    """Ensure tables exist and clean them up after tests."""
    # Reflect existing tables from database
    metadata.reflect(bind=test_engine)

    yield

    # Cleanup: delete test data after each test
    with get_connection(test_engine) as conn:
        # Delete in order respecting foreign keys
        if 'projects' in metadata.tables:
            conn.execute(text("DELETE FROM projects WHERE slug LIKE 'test-%' OR slug = 'default'"))
        if 'workspace_members' in metadata.tables:
            conn.execute(text("DELETE FROM workspace_members WHERE workspace_id IN (SELECT id FROM workspaces WHERE slug LIKE 'test-%')"))
        if 'workspaces' in metadata.tables:
            conn.execute(text("DELETE FROM workspaces WHERE slug LIKE 'test-%'"))
        if 'users' in metadata.tables:
            conn.execute(text("DELETE FROM users WHERE email LIKE 'test-%@example.com'"))
        conn.commit()


class TestHelperFunctions:
    """Unit tests for helper functions."""

    def test_generate_slug_simple(self):
        """Test slug generation from simple name."""
        assert generate_slug("Bogdan") == "bogdan"
        assert generate_slug("John") == "john"

    def test_generate_slug_multiple_words(self):
        """Test slug generation extracts first word."""
        assert generate_slug("Bogdan Pshonyak") == "bogdan"
        assert generate_slug("John Doe Smith") == "john"

    def test_generate_slug_special_chars(self):
        """Test slug generation handles special characters."""
        assert generate_slug("José García") == "jos-garc-a"
        assert generate_slug("François-Pierre") == "fran-ois-pierre"

    def test_generate_slug_empty(self):
        """Test slug generation with empty string."""
        assert generate_slug("") == "user"
        assert generate_slug("   ") == "user"

    def test_get_first_name_simple(self):
        """Test first name extraction from simple name."""
        assert get_first_name("Bogdan") == "Bogdan"
        assert get_first_name("Alice") == "Alice"

    def test_get_first_name_multiple_words(self):
        """Test first name extraction from full name."""
        assert get_first_name("Bogdan Pshonyak") == "Bogdan"
        assert get_first_name("John Doe Smith") == "John"

    def test_get_first_name_empty(self):
        """Test first name extraction with None or empty."""
        assert get_first_name(None) == "User"
        assert get_first_name("") == "User"
        assert get_first_name("   ") == "User"


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set - skipping live database tests"
)
class TestProvisioningIntegration:
    """Integration tests for provisioning logic (requires database)."""

    def test_provision_workspace_and_project(self, test_engine, setup_tables):
        """Test provisioning creates all required records."""
        with get_connection(test_engine) as conn:
            # Create test user
            user_result = conn.execute(
                users_table.insert().values(
                    clerk_user_id="test_clerk_123",
                    email="test-bogdan@example.com",
                    name="Bogdan Pshonyak"
                ).returning(users_table.c.id)
            )
            user_id = user_result.fetchone()[0]
            conn.commit()

            # Reflect tables
            metadata.reflect(bind=conn)
            workspaces_table = metadata.tables['workspaces']
            workspace_members_table = metadata.tables['workspace_members']
            projects_table = metadata.tables['projects']

            # Provision workspace and project
            workspace_id, project_id = provision_workspace_and_project(
                conn, user_id, "Bogdan Pshonyak", "test-bogdan@example.com"
            )
            conn.commit()

            # Verify workspace created
            workspace = conn.execute(
                select(workspaces_table).where(workspaces_table.c.id == workspace_id)
            ).fetchone()
            assert workspace is not None
            assert workspace.name == "Bogdan's Projects"
            assert workspace.type == "personal"
            assert workspace.owner_id == user_id
            assert workspace.slug == "bogdan"

            # Verify workspace membership
            membership = conn.execute(
                select(workspace_members_table).where(
                    workspace_members_table.c.workspace_id == workspace_id,
                    workspace_members_table.c.user_id == user_id
                )
            ).fetchone()
            assert membership is not None
            assert membership.role == "owner"

            # Verify project created
            project = conn.execute(
                select(projects_table).where(projects_table.c.id == project_id)
            ).fetchone()
            assert project is not None
            assert project.name == "Bogdan's Project"
            assert project.slug == "default"
            assert project.workspace_id == workspace_id

    def test_provision_workspace_unique_slug(self, test_engine, setup_tables):
        """Test provisioning handles duplicate slugs."""
        with get_connection(test_engine) as conn:
            # Create two test users with same name
            user1_result = conn.execute(
                users_table.insert().values(
                    clerk_user_id="test_clerk_456",
                    email="test-john1@example.com",
                    name="John Doe"
                ).returning(users_table.c.id)
            )
            user1_id = user1_result.fetchone()[0]

            user2_result = conn.execute(
                users_table.insert().values(
                    clerk_user_id="test_clerk_789",
                    email="test-john2@example.com",
                    name="John Doe"
                ).returning(users_table.c.id)
            )
            user2_id = user2_result.fetchone()[0]
            conn.commit()

            # Reflect tables
            metadata.reflect(bind=conn)
            workspaces_table = metadata.tables['workspaces']

            # Provision first workspace
            workspace1_id, _ = provision_workspace_and_project(
                conn, user1_id, "John Doe", "test-john1@example.com"
            )
            conn.commit()

            # Provision second workspace (should get unique slug)
            workspace2_id, _ = provision_workspace_and_project(
                conn, user2_id, "John Doe", "test-john2@example.com"
            )
            conn.commit()

            # Verify both workspaces have unique slugs
            workspace1 = conn.execute(
                select(workspaces_table).where(workspaces_table.c.id == workspace1_id)
            ).fetchone()
            workspace2 = conn.execute(
                select(workspaces_table).where(workspaces_table.c.id == workspace2_id)
            ).fetchone()

            assert workspace1.slug == "john"
            assert workspace2.slug == "john-1"

    def test_provision_workspace_first_name_only(self, test_engine, setup_tables):
        """Test provisioning with first name only (no last name)."""
        with get_connection(test_engine) as conn:
            # Create test user
            user_result = conn.execute(
                users_table.insert().values(
                    clerk_user_id="test_clerk_999",
                    email="test-alice@example.com",
                    name="Alice"
                ).returning(users_table.c.id)
            )
            user_id = user_result.fetchone()[0]
            conn.commit()

            # Reflect tables
            metadata.reflect(bind=conn)
            workspaces_table = metadata.tables['workspaces']
            projects_table = metadata.tables['projects']

            # Provision workspace and project
            workspace_id, project_id = provision_workspace_and_project(
                conn, user_id, "Alice", "test-alice@example.com"
            )
            conn.commit()

            # Verify names are correct
            workspace = conn.execute(
                select(workspaces_table).where(workspaces_table.c.id == workspace_id)
            ).fetchone()
            project = conn.execute(
                select(projects_table).where(projects_table.c.id == project_id)
            ).fetchone()

            assert workspace.name == "Alice's Projects"
            assert project.name == "Alice's Project"

    def test_get_or_create_workspace_creates_new(self, test_engine, setup_tables):
        """Test get_or_create_workspace creates workspace if missing."""
        with get_connection(test_engine) as conn:
            # Create test user without workspace
            user_result = conn.execute(
                users_table.insert().values(
                    clerk_user_id="test_clerk_lazy_1",
                    email="test-lazy1@example.com",
                    name="Lazy User"
                ).returning(users_table.c.id)
            )
            user_id = user_result.fetchone()[0]
            conn.commit()

        # Call get_or_create_workspace (should create)
        workspace_id, project_id = get_or_create_workspace(
            test_engine, user_id, "Lazy User", "test-lazy1@example.com"
        )

        # Verify workspace and project exist
        assert isinstance(workspace_id, UUID)
        assert isinstance(project_id, UUID)

        with get_connection(test_engine) as conn:
            metadata.reflect(bind=conn)
            workspaces_table = metadata.tables['workspaces']

            workspace = conn.execute(
                select(workspaces_table).where(workspaces_table.c.id == workspace_id)
            ).fetchone()
            assert workspace is not None
            assert workspace.name == "Lazy's Projects"

    def test_get_or_create_workspace_returns_existing(self, test_engine, setup_tables):
        """Test get_or_create_workspace returns existing workspace."""
        with get_connection(test_engine) as conn:
            # Create test user
            user_result = conn.execute(
                users_table.insert().values(
                    clerk_user_id="test_clerk_existing",
                    email="test-existing@example.com",
                    name="Existing User"
                ).returning(users_table.c.id)
            )
            user_id = user_result.fetchone()[0]
            conn.commit()

            # Manually provision workspace
            metadata.reflect(bind=conn)
            original_workspace_id, original_project_id = provision_workspace_and_project(
                conn, user_id, "Existing User", "test-existing@example.com"
            )
            conn.commit()

        # Call get_or_create_workspace (should return existing)
        workspace_id, project_id = get_or_create_workspace(
            test_engine, user_id, "Existing User", "test-existing@example.com"
        )

        # Verify it returns the same IDs
        assert workspace_id == original_workspace_id
        assert project_id == original_project_id

    def test_get_or_create_workspace_handles_race_condition(self, test_engine, setup_tables):
        """Test get_or_create_workspace handles concurrent requests gracefully."""
        # This simulates the race condition where:
        # 1. User logs in before webhook completes
        # 2. First API call triggers lazy provisioning
        # 3. Webhook completes shortly after

        with get_connection(test_engine) as conn:
            # Create test user (simulating immediate login after signup)
            user_result = conn.execute(
                users_table.insert().values(
                    clerk_user_id="test_clerk_race",
                    email="test-race@example.com",
                    name="Race User"
                ).returning(users_table.c.id)
            )
            user_id = user_result.fetchone()[0]
            conn.commit()

        # First call (simulating first API request)
        workspace_id_1, project_id_1 = get_or_create_workspace(
            test_engine, user_id, "Race User", "test-race@example.com"
        )

        # Second call (simulating webhook completing)
        workspace_id_2, project_id_2 = get_or_create_workspace(
            test_engine, user_id, "Race User", "test-race@example.com"
        )

        # Both should return the same workspace/project
        assert workspace_id_1 == workspace_id_2
        assert project_id_1 == project_id_2

        # Verify only one workspace was created
        with get_connection(test_engine) as conn:
            metadata.reflect(bind=conn)
            workspaces_table = metadata.tables['workspaces']

            workspaces = conn.execute(
                select(workspaces_table).where(
                    workspaces_table.c.owner_id == user_id
                )
            ).fetchall()
            assert len(workspaces) == 1