"""Integration tests for API key service."""

import pytest
from uuid import UUID
from datetime import datetime, timedelta
from dakora_server.core.api_keys.service import (
    APIKeyService,
    APIKeyLimitExceeded,
    InvalidExpiration,
    APIKeyNotFound,
)
from dakora_server.core.database import create_db_engine


@pytest.mark.integration
class TestAPIKeyService:
    """Test API key service business logic."""

    @pytest.fixture
    def service(self, db_engine):
        """Create an API key service instance."""
        return APIKeyService(db_engine)

    def test_create_key_success(self, service, test_project):
        """Test successful API key creation."""
        project_id, _, user_id = test_project

        result = service.create_key(
            user_id=user_id,
            project_id=project_id,
            name="Test Key",
            expires_in_days=90,
        )

        # Verify response
        assert result.id is not None
        assert result.name == "Test Key"
        assert result.key.startswith("dkr_")
        assert result.key_prefix == result.key[:8]
        assert result.expires_at is not None
        assert result.created_at is not None

        # Verify expiration is approximately 90 days
        expected_expiry = datetime.utcnow() + timedelta(days=90)
        assert abs((result.expires_at - expected_expiry).total_seconds()) < 60

    def test_create_key_no_expiration(self, service, test_project):
        """Test creating key without expiration."""
        project_id, _, user_id = test_project

        result = service.create_key(
            user_id=user_id,
            project_id=project_id,
            name="Never Expires",
            expires_in_days=None,
        )

        assert result.expires_at is None

    def test_create_key_invalid_expiration(self, service, test_project):
        """Test creating key with invalid expiration."""
        project_id, _, user_id = test_project

        with pytest.raises(InvalidExpiration):
            service.create_key(
                user_id=user_id,
                project_id=project_id,
                expires_in_days=999,
            )

    def test_create_key_limit_exceeded(self, service, test_project):
        """Test that creating too many keys raises an error."""
        project_id, _, user_id = test_project

        # Create maximum number of keys
        for i in range(4):
            service.create_key(
                user_id=user_id,
                project_id=project_id,
                name=f"Key {i}",
            )

        # Try to create one more
        with pytest.raises(APIKeyLimitExceeded):
            service.create_key(
                user_id=user_id,
                project_id=project_id,
                name="Too Many",
            )

    def test_list_keys(self, service, test_project):
        """Test listing API keys."""
        project_id, _, user_id = test_project

        # Create a few keys
        key1 = service.create_key(
            user_id=user_id,
            project_id=project_id,
            name="Key 1",
        )
        key2 = service.create_key(
            user_id=user_id,
            project_id=project_id,
            name="Key 2",
            expires_in_days=30,
        )

        # List keys
        result = service.list_keys(
            user_id=user_id,
            project_id=project_id,
        )

        assert result.count == 2
        assert result.limit == 4
        assert len(result.keys) == 2

        # Verify key data
        keys_by_name = {k.name: k for k in result.keys}
        assert "Key 1" in keys_by_name
        assert "Key 2" in keys_by_name

        # Check that keys are in the preview format (prefix...suffix)
        for key in result.keys:
            assert key.key_preview.startswith("dkr_")
            assert "..." in key.key_preview
            assert len(key.key_preview) == 15  # 8 char prefix + ... + 4 char suffix

    def test_get_key(self, service, test_project):
        """Test getting a specific API key."""
        project_id, _, user_id = test_project

        created = service.create_key(
            user_id=user_id,
            project_id=project_id,
            name="Test Key",
        )

        result = service.get_key(
            user_id=user_id,
            project_id=project_id,
            key_id=created.id,
        )

        assert result.id == created.id
        assert result.name == "Test Key"
        assert result.key_preview.startswith("dkr_")
        assert "..." in result.key_preview
        assert len(result.key_preview) == 15  # 8 char prefix + ... + 4 char suffix

    def test_get_key_not_found(self, service, test_project):
        """Test getting non-existent key."""
        from uuid import uuid4
        project_id, _, user_id = test_project

        with pytest.raises(APIKeyNotFound):
            service.get_key(
                user_id=user_id,
                project_id=project_id,
                key_id=uuid4(),
            )

    def test_revoke_key(self, service, test_project):
        """Test revoking an API key."""
        project_id, _, user_id = test_project

        created = service.create_key(
            user_id=user_id,
            project_id=project_id,
            name="To Revoke",
        )

        # Revoke the key
        service.revoke_key(
            user_id=user_id,
            project_id=project_id,
            key_id=created.id,
        )

        # Key should no longer be listed
        result = service.list_keys(
            user_id=user_id,
            project_id=project_id,
        )
        assert result.count == 0

    def test_validate_key_valid(self, service, test_project):
        """Test validating a valid key."""
        project_id, _, user_id = test_project

        created = service.create_key(
            user_id=user_id,
            project_id=project_id,
            name="Valid Key",
        )

        # Validate the key
        result = service.validate_key(created.key)

        assert result.valid is True
        assert result.user_id == user_id
        assert result.project_id == project_id
        assert result.expired is False
        assert result.revoked is False

    def test_validate_key_invalid(self, service):
        """Test validating an invalid key."""
        result = service.validate_key("dkr_invalidkey123")

        assert result.valid is False
        assert result.user_id is None
        assert result.project_id is None

    def test_validate_key_revoked(self, service, test_project):
        """Test validating a revoked key."""
        project_id, _, user_id = test_project

        created = service.create_key(
            user_id=user_id,
            project_id=project_id,
            name="To Revoke",
        )

        # Revoke the key
        service.revoke_key(
            user_id=user_id,
            project_id=project_id,
            key_id=created.id,
        )

        # Validate should return revoked
        result = service.validate_key(created.key)

        assert result.valid is False
        assert result.revoked is True