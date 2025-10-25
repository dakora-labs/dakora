"""Integration tests for Clerk webhook provisioning flow."""

import pytest
from sqlalchemy import select, text

from dakora_server.core.database import metadata


@pytest.fixture(autouse=True)
def cleanup_webhook_tests(db_connection):
    """Clean up test data created by webhook tests."""
    yield

    # Rollback any failed transactions first
    db_connection.rollback()

    # Cleanup after each test - same pattern as provisioning tests
    metadata.reflect(bind=db_connection)

    if 'users' in metadata.tables:
        # Clean up webhook test data
        db_connection.execute(text("""
            DELETE FROM projects WHERE workspace_id IN (
                SELECT id FROM workspaces WHERE owner_id IN (
                    SELECT id FROM users WHERE
                        email LIKE 'webhook-test-%@example.com' OR
                        clerk_user_id LIKE 'user_webhook_test_%'
                )
            )
        """))
        db_connection.execute(text("""
            DELETE FROM workspace_members WHERE user_id IN (
                SELECT id FROM users WHERE
                    email LIKE 'webhook-test-%@example.com' OR
                    clerk_user_id LIKE 'user_webhook_test_%'
            )
        """))
        db_connection.execute(text("""
            DELETE FROM workspaces WHERE owner_id IN (
                SELECT id FROM users WHERE
                    email LIKE 'webhook-test-%@example.com' OR
                    clerk_user_id LIKE 'user_webhook_test_%'
            )
        """))
        db_connection.execute(text("""
            DELETE FROM users WHERE
                email LIKE 'webhook-test-%@example.com' OR
                clerk_user_id LIKE 'user_webhook_test_%'
        """))
        db_connection.commit()


@pytest.mark.integration
class TestWebhookProvisioning:
    """Integration tests for webhook-triggered provisioning."""

    def test_webhook_creates_user_workspace_and_project(self, test_client, db_connection):
        """Test webhook creates user, workspace, and project in one transaction."""
        # Mock Clerk webhook payload
        webhook_payload = {
            "type": "user.created",
            "data": {
                "id": "user_webhook_test_123",
                "email_addresses": [
                    {
                        "id": "email_123",
                        "email_address": "webhook-test-john@example.com"
                    }
                ],
                "primary_email_address_id": "email_123",
                "first_name": "John",
                "last_name": "Doe"
            }
        }

        # Send webhook request (skipping signature verification for test)
        response = test_client.post("/api/webhooks/clerk", json=webhook_payload)
        assert response.status_code == 200

        response_data = response.json()
        assert response_data["status"] == "success"
        assert "workspace_id" in response_data
        assert "project_id" in response_data

        # Verify user was created
        metadata.reflect(bind=db_connection)
        users_table = metadata.tables['users']
        workspaces_table = metadata.tables['workspaces']
        workspace_members_table = metadata.tables['workspace_members']
        projects_table = metadata.tables['projects']

        # Check user
        user = db_connection.execute(
            select(users_table).where(
                users_table.c.clerk_user_id == "user_webhook_test_123"
            )
        ).fetchone()
        assert user is not None
        assert user.email == "webhook-test-john@example.com"
        assert user.name == "John Doe"

        # Check workspace
        workspace = db_connection.execute(
            select(workspaces_table).where(
                workspaces_table.c.owner_id == user.id
            )
        ).fetchone()
        assert workspace is not None
        assert workspace.name == "John's Projects"
        assert workspace.slug == "webhook-test-john" or workspace.slug.startswith("john")
        assert workspace.type == "personal"

        # Check workspace membership
        membership = db_connection.execute(
            select(workspace_members_table).where(
                workspace_members_table.c.workspace_id == workspace.id,
                workspace_members_table.c.user_id == user.id
            )
        ).fetchone()
        assert membership is not None
        assert membership.role == "owner"

        # Check project
        project = db_connection.execute(
            select(projects_table).where(
                projects_table.c.workspace_id == workspace.id
            )
        ).fetchone()
        assert project is not None
        assert project.name == "John's Project"
        assert project.slug == "default"

    def test_webhook_first_name_only(self, test_client, db_connection):
        """Test webhook with first name only (no last name)."""
        webhook_payload = {
            "type": "user.created",
            "data": {
                "id": "user_webhook_test_456",
                "email_addresses": [
                    {
                        "id": "email_456",
                        "email_address": "webhook-test-alice@example.com"
                    }
                ],
                "primary_email_address_id": "email_456",
                "first_name": "Alice",
                "last_name": None
            }
        }

        response = test_client.post("/api/webhooks/clerk", json=webhook_payload)
        assert response.status_code == 200

        # Verify workspace and project names
        metadata.reflect(bind=db_connection)
        users_table = metadata.tables['users']
        workspaces_table = metadata.tables['workspaces']
        projects_table = metadata.tables['projects']

        user = db_connection.execute(
            select(users_table).where(
                users_table.c.clerk_user_id == "user_webhook_test_456"
            )
        ).fetchone()
        assert user.name == "Alice"

        workspace = db_connection.execute(
            select(workspaces_table).where(
                workspaces_table.c.owner_id == user.id
            )
        ).fetchone()
        assert workspace.name == "Alice's Projects"

        project = db_connection.execute(
            select(projects_table).where(
                projects_table.c.workspace_id == workspace.id
            )
        ).fetchone()
        assert project.name == "Alice's Project"

    def test_webhook_multiple_names(self, test_client, db_connection):
        """Test webhook extracts first name from multiple words."""
        webhook_payload = {
            "type": "user.created",
            "data": {
                "id": "user_webhook_test_789",
                "email_addresses": [
                    {
                        "id": "email_789",
                        "email_address": "webhook-test-maria@example.com"
                    }
                ],
                "primary_email_address_id": "email_789",
                "first_name": "Maria José",
                "last_name": "García Fernández"
            }
        }

        response = test_client.post("/api/webhooks/clerk", json=webhook_payload)
        assert response.status_code == 200

        # Verify first name is extracted correctly
        metadata.reflect(bind=db_connection)
        users_table = metadata.tables['users']
        workspaces_table = metadata.tables['workspaces']

        user = db_connection.execute(
            select(users_table).where(
                users_table.c.clerk_user_id == "user_webhook_test_789"
            )
        ).fetchone()

        workspace = db_connection.execute(
            select(workspaces_table).where(
                workspaces_table.c.owner_id == user.id
            )
        ).fetchone()
        # Should use "Maria" from "Maria José"
        assert workspace.name == "Maria's Projects"

    def test_webhook_idempotent(self, test_client, db_connection):
        """Test webhook is idempotent (duplicate calls don't create duplicates)."""
        webhook_payload = {
            "type": "user.created",
            "data": {
                "id": "user_webhook_test_idem",
                "email_addresses": [
                    {
                        "id": "email_idem",
                        "email_address": "webhook-test-idem@example.com"
                    }
                ],
                "primary_email_address_id": "email_idem",
                "first_name": "Idem",
                "last_name": "Potent"
            }
        }

        # First call
        response1 = test_client.post("/api/webhooks/clerk", json=webhook_payload)
        assert response1.status_code == 200
        assert "workspace_id" in response1.json()

        # Second call (duplicate)
        response2 = test_client.post("/api/webhooks/clerk", json=webhook_payload)
        assert response2.status_code == 200
        assert response2.json()["message"] == "User already exists"

        # Verify only one workspace was created
        metadata.reflect(bind=db_connection)
        users_table = metadata.tables['users']
        workspaces_table = metadata.tables['workspaces']

        user = db_connection.execute(
            select(users_table).where(
                users_table.c.clerk_user_id == "user_webhook_test_idem"
            )
        ).fetchone()

        workspaces = db_connection.execute(
            select(workspaces_table).where(
                workspaces_table.c.owner_id == user.id
            )
        ).fetchall()
        assert len(workspaces) == 1

    def test_webhook_handles_missing_required_fields(self, test_client):
        """Test webhook returns error for missing required fields."""
        # Missing email
        webhook_payload = {
            "type": "user.created",
            "data": {
                "id": "user_webhook_test_error",
                "email_addresses": [],
                "first_name": "Test",
                "last_name": "User"
            }
        }

        response = test_client.post("/api/webhooks/clerk", json=webhook_payload)
        assert response.status_code == 400
        assert "Missing required fields" in response.json()["detail"]