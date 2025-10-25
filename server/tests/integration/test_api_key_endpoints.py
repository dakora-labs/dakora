"""Integration tests for API key endpoints."""

import pytest
from dakora_server.core.database import api_keys_table
from dakora_server.core.api_keys.generator import APIKeyGenerator
from sqlalchemy import insert, delete
from datetime import datetime, timedelta
from uuid import UUID


@pytest.mark.integration
class TestAPIKeyEndpoints:
    """Integration tests for API key management endpoints."""

    def test_create_api_key(self, test_project, test_client, override_auth_dependencies, db_connection):
        """Test creating an API key via API."""
        project_id, _, _ = test_project

        response = test_client.post(
            f"/api/projects/{project_id}/api-keys",
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

    def test_create_api_key_no_expiration(self, test_project, test_client, override_auth_dependencies, db_connection):
        """Test creating key without expiration."""
        project_id, _, _ = test_project

        response = test_client.post(
            f"/api/projects/{project_id}/api-keys",
            json={
                "name": "Never Expires",
                "expires_in_days": None,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["expires_at"] is None

    def test_create_api_key_invalid_expiration(self, test_project, test_client, override_auth_dependencies, db_connection):
        """Test creating key with invalid expiration."""
        project_id, _, _ = test_project

        response = test_client.post(
            f"/api/projects/{project_id}/api-keys",
            json={
                "name": "Invalid",
                "expires_in_days": 999,
            },
        )

        assert response.status_code == 400
        assert "expires_in_days" in response.json()["detail"].lower()

    def test_create_api_key_limit_exceeded(self, test_project, test_client, override_auth_dependencies, db_connection):
        """Test that key limit is enforced."""
        project_id, _, owner_id = test_project

        # Create 4 keys directly using db_connection
        for i in range(4):
            full_key, key_hash = APIKeyGenerator.generate()
            key_prefix = APIKeyGenerator.get_prefix(full_key)
            key_suffix = APIKeyGenerator.get_suffix(full_key)

            db_connection.execute(
                insert(api_keys_table).values(
                    user_id=owner_id,
                    project_id=project_id,
                    name=f"Key {i}",
                    key_prefix=key_prefix,
                    key_suffix=key_suffix,
                    key_hash=key_hash,
                )
            )
        db_connection.commit()

        # Try to create via API
        response = test_client.post(
            f"/api/projects/{project_id}/api-keys",
            json={"name": "Too Many"},
        )

        assert response.status_code == 400
        assert "maximum" in response.json()["detail"].lower()

    def test_list_api_keys(self, test_project, test_client, override_auth_dependencies, db_connection):
        """Test listing API keys."""
        project_id, _, owner_id = test_project

        # Create key 1
        full_key1, key_hash1 = APIKeyGenerator.generate()
        db_connection.execute(
            insert(api_keys_table).values(
                user_id=owner_id,
                project_id=project_id,
                name="Key 1",
                key_prefix=APIKeyGenerator.get_prefix(full_key1),
                key_suffix=APIKeyGenerator.get_suffix(full_key1),
                key_hash=key_hash1,
            )
        )

        # Create key 2 with expiration
        full_key2, key_hash2 = APIKeyGenerator.generate()
        expires_at = datetime.utcnow() + timedelta(days=30)
        db_connection.execute(
            insert(api_keys_table).values(
                user_id=owner_id,
                project_id=project_id,
                name="Key 2",
                key_prefix=APIKeyGenerator.get_prefix(full_key2),
                key_suffix=APIKeyGenerator.get_suffix(full_key2),
                key_hash=key_hash2,
                expires_at=expires_at,
            )
        )
        db_connection.commit()

        # List keys
        response = test_client.get(f"/api/projects/{project_id}/api-keys")

        assert response.status_code == 200
        data = response.json()

        assert data["count"] == 2
        assert data["limit"] == 4
        assert len(data["keys"]) == 2

        # Check that keys are masked
        for key in data["keys"]:
            assert key["key_preview"].startswith("dkr_")
            assert "..." in key["key_preview"]
            assert len(key["key_preview"]) == 15  # 8 char prefix + ... + 4 char suffix
            assert "key" not in key  # Full key should not be included

    def test_get_api_key(self, test_project, test_client, override_auth_dependencies, db_connection):
        """Test getting a specific API key."""
        project_id, _, owner_id = test_project

        # Create a key
        full_key, key_hash = APIKeyGenerator.generate()
        result = db_connection.execute(
            insert(api_keys_table).values(
                user_id=owner_id,
                project_id=project_id,
                name="Test Key",
                key_prefix=APIKeyGenerator.get_prefix(full_key),
                key_suffix=APIKeyGenerator.get_suffix(full_key),
                key_hash=key_hash,
            ).returning(api_keys_table.c.id)
        )
        key_id = result.scalar()
        db_connection.commit()

        # Get the key
        response = test_client.get(
            f"/api/projects/{project_id}/api-keys/{key_id}"
        )

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == str(key_id)
        assert data["name"] == "Test Key"
        assert data["key_preview"].startswith("dkr_")
        assert "..." in data["key_preview"]
        assert len(data["key_preview"]) == 15  # 8 char prefix + ... + 4 char suffix
        assert "key" not in data

    def test_get_api_key_not_found(self, test_project, test_client, override_auth_dependencies, db_connection):
        """Test getting non-existent key."""
        from uuid import uuid4
        project_id, _, _ = test_project

        response = test_client.get(
            f"/api/projects/{project_id}/api-keys/{uuid4()}"
        )

        assert response.status_code == 404

    def test_revoke_api_key(self, test_project, test_client, override_auth_dependencies, db_connection):
        """Test revoking an API key."""
        project_id, _, owner_id = test_project

        # Create a key
        full_key, key_hash = APIKeyGenerator.generate()
        result = db_connection.execute(
            insert(api_keys_table).values(
                user_id=owner_id,
                project_id=project_id,
                name="To Revoke",
                key_prefix=APIKeyGenerator.get_prefix(full_key),
                key_suffix=APIKeyGenerator.get_suffix(full_key),
                key_hash=key_hash,
            ).returning(api_keys_table.c.id)
        )
        key_id = result.scalar()
        db_connection.commit()

        # Revoke the key
        response = test_client.delete(
            f"/api/projects/{project_id}/api-keys/{key_id}"
        )

        assert response.status_code == 204

        # Verify key is no longer listed
        list_response = test_client.get(f"/api/projects/{project_id}/api-keys")
        assert list_response.json()["count"] == 0

    def test_revoke_api_key_not_found(self, test_project, test_client, override_auth_dependencies, db_connection):
        """Test revoking non-existent key."""
        from uuid import uuid4
        project_id, _, _ = test_project

        response = test_client.delete(
            f"/api/projects/{project_id}/api-keys/{uuid4()}"
        )

        assert response.status_code == 404

    def test_api_key_workflow(self, test_project, test_client, override_auth_dependencies, db_connection):
        """Test complete workflow: create, list, get, revoke."""
        project_id, _, _ = test_project

        # 1. Create a key
        create_response = test_client.post(
            f"/api/projects/{project_id}/api-keys",
            json={"name": "Workflow Test", "expires_in_days": 90},
        )
        assert create_response.status_code == 201
        created_key = create_response.json()
        key_id = created_key["id"]

        # 2. List keys - should see 1
        list_response = test_client.get(f"/api/projects/{project_id}/api-keys")
        assert list_response.json()["count"] == 1

        # 3. Get specific key
        get_response = test_client.get(
            f"/api/projects/{project_id}/api-keys/{key_id}"
        )
        assert get_response.status_code == 200
        assert get_response.json()["name"] == "Workflow Test"

        # 4. Revoke key
        revoke_response = test_client.delete(
            f"/api/projects/{project_id}/api-keys/{key_id}"
        )
        assert revoke_response.status_code == 204

        # 5. List keys - should see 0
        list_response2 = test_client.get(f"/api/projects/{project_id}/api-keys")
        assert list_response2.json()["count"] == 0