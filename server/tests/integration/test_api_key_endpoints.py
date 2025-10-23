"""Integration tests for API key endpoints."""

import pytest
import os
from starlette.testclient import TestClient
from dakora_server.main import create_app
from dakora_server.core.api_keys.service import APIKeyService
from dakora_server.core.database import create_db_engine
from uuid import UUID


@pytest.fixture
def client(test_user_id, test_project_id):
    """Create test client with auth dependencies overridden."""
    from dakora_server.auth import get_current_user_id, validate_project_access

    # Override auth dependencies to return test IDs
    app = create_app()
    app.dependency_overrides[get_current_user_id] = lambda: test_user_id
    app.dependency_overrides[validate_project_access] = lambda: UUID(test_project_id)

    client = TestClient(app)
    yield client

    # Clean up
    app.dependency_overrides.clear()


@pytest.mark.integration
class TestAPIKeyEndpoints:
    """Integration tests for API key management endpoints."""

    def test_create_api_key(self, client, test_project_id, clean_api_keys):
        """Test creating an API key via API."""
        response = client.post(
            f"/api/projects/{test_project_id}/api-keys",
            json={
                "name": "Production Key",
                "expires_in_days": 365,
            },
        )

        assert response.status_code == 201
        data = response.json()

        # Check response structure
        assert "id" in data
        assert data["name"] == "Production Key"
        assert "key" in data
        assert data["key"].startswith("dkr_")
        assert "key_prefix" in data
        assert "created_at" in data
        assert "expires_at" in data

    def test_create_api_key_no_expiration(self, client, test_project_id, clean_api_keys):
        """Test creating key without expiration."""
        response = client.post(
            f"/api/projects/{test_project_id}/api-keys",
            json={
                "name": "Never Expires",
                "expires_in_days": None,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["expires_at"] is None

    def test_create_api_key_invalid_expiration(self, client, test_project_id):
        """Test creating key with invalid expiration."""
        response = client.post(
            f"/api/projects/{test_project_id}/api-keys",
            json={
                "name": "Invalid",
                "expires_in_days": 999,
            },
        )

        assert response.status_code == 400
        assert "expires_in_days" in response.json()["detail"].lower()

    def test_create_api_key_limit_exceeded(self, client, test_project_id, test_user_id, clean_api_keys):
        """Test that key limit is enforced."""
        # Create 4 keys directly via service
        service = APIKeyService(create_db_engine())
        for i in range(4):
            service.create_key(
                user_id=test_user_id,
                project_id=UUID(test_project_id),
                name=f"Key {i}",
            )

        # Try to create via API
        response = client.post(
            f"/api/projects/{test_project_id}/api-keys",
            json={"name": "Too Many"},
        )

        assert response.status_code == 400
        assert "maximum" in response.json()["detail"].lower()

    def test_list_api_keys(self, client, test_project_id, test_user_id, clean_api_keys):
        """Test listing API keys."""
        # Create some keys
        service = APIKeyService(create_db_engine())
        service.create_key(
            user_id=test_user_id,
            project_id=UUID(test_project_id),
            name="Key 1",
        )
        service.create_key(
            user_id=test_user_id,
            project_id=UUID(test_project_id),
            name="Key 2",
            expires_in_days=30,
        )

        # List keys
        response = client.get(f"/api/projects/{test_project_id}/api-keys")

        assert response.status_code == 200
        data = response.json()

        assert data["count"] == 2
        assert data["limit"] == 4
        assert len(data["keys"]) == 2

        # Check that keys are masked
        for key in data["keys"]:
            assert key["key_preview"].endswith("***...***")
            assert "key" not in key  # Full key should not be included

    def test_get_api_key(self, client, test_project_id, test_user_id, clean_api_keys):
        """Test getting a specific API key."""
        # Create a key
        service = APIKeyService(create_db_engine())
        created = service.create_key(
            user_id=test_user_id,
            project_id=UUID(test_project_id),
            name="Test Key",
        )

        # Get the key
        response = client.get(
            f"/api/projects/{test_project_id}/api-keys/{created.id}"
        )

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == str(created.id)
        assert data["name"] == "Test Key"
        assert data["key_preview"].endswith("***...***")
        assert "key" not in data

    def test_get_api_key_not_found(self, client, test_project_id):
        """Test getting non-existent key."""
        from uuid import uuid4

        response = client.get(
            f"/api/projects/{test_project_id}/api-keys/{uuid4()}"
        )

        assert response.status_code == 404

    def test_revoke_api_key(self, client, test_project_id, test_user_id, clean_api_keys):
        """Test revoking an API key."""
        # Create a key
        service = APIKeyService(create_db_engine())
        created = service.create_key(
            user_id=test_user_id,
            project_id=UUID(test_project_id),
            name="To Revoke",
        )

        # Revoke the key
        response = client.delete(
            f"/api/projects/{test_project_id}/api-keys/{created.id}"
        )

        assert response.status_code == 204

        # Verify key is no longer listed
        list_response = client.get(f"/api/projects/{test_project_id}/api-keys")
        assert list_response.json()["count"] == 0

    def test_revoke_api_key_not_found(self, client, test_project_id):
        """Test revoking non-existent key."""
        from uuid import uuid4

        response = client.delete(
            f"/api/projects/{test_project_id}/api-keys/{uuid4()}"
        )

        assert response.status_code == 404

    def test_api_key_workflow(self, client, test_project_id, clean_api_keys):
        """Test complete workflow: create, list, get, revoke."""
        # 1. Create a key
        create_response = client.post(
            f"/api/projects/{test_project_id}/api-keys",
            json={"name": "Workflow Test", "expires_in_days": 90},
        )
        assert create_response.status_code == 201
        created_key = create_response.json()
        key_id = created_key["id"]

        # 2. List keys - should see 1
        list_response = client.get(f"/api/projects/{test_project_id}/api-keys")
        assert list_response.json()["count"] == 1

        # 3. Get specific key
        get_response = client.get(
            f"/api/projects/{test_project_id}/api-keys/{key_id}"
        )
        assert get_response.status_code == 200
        assert get_response.json()["name"] == "Workflow Test"

        # 4. Revoke key
        revoke_response = client.delete(
            f"/api/projects/{test_project_id}/api-keys/{key_id}"
        )
        assert revoke_response.status_code == 204

        # 5. List keys - should see 0
        list_response2 = client.get(f"/api/projects/{test_project_id}/api-keys")
        assert list_response2.json()["count"] == 0