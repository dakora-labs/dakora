"""Unit tests for API key service."""

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


class TestAPIKeyService:
    """Test API key service business logic."""

    @pytest.fixture
    def service(self):
        """Create an API key service instance."""
        engine = create_db_engine()
        return APIKeyService(engine)

    def test_create_key_success(self, service, test_user_id, test_project_id, clean_api_keys):
        """Test successful API key creation."""
        result = service.create_key(
            user_id=test_user_id,
            project_id=UUID(test_project_id),
            name="Test Key",
            expires_in_days=90,
        )

        # Verify response
        assert result.id is not None
        assert result.name == "Test Key"
        assert result.key.startswith("dkr_")
        assert result.key_prefix == result.key[:12]
        assert result.expires_at is not None
        assert result.created_at is not None

        # Verify expiration is approximately 90 days
        expected_expiry = datetime.utcnow() + timedelta(days=90)
        assert abs((result.expires_at - expected_expiry).total_seconds()) < 60

    def test_create_key_no_expiration(self, service, test_user_id, test_project_id, clean_api_keys):
        """Test creating key without expiration."""
        result = service.create_key(
            user_id=test_user_id,
            project_id=UUID(test_project_id),
            name="Never Expires",
            expires_in_days=None,
        )

        assert result.expires_at is None

    def test_create_key_invalid_expiration(self, service, test_user_id, test_project_id):
        """Test creating key with invalid expiration."""
        with pytest.raises(InvalidExpiration):
            service.create_key(
                user_id=test_user_id,
                project_id=UUID(test_project_id),
                expires_in_days=999,
            )

    def test_create_key_limit_exceeded(self, service, test_user_id, test_project_id, clean_api_keys):
        """Test that creating too many keys raises an error."""
        # Create maximum number of keys
        for i in range(4):
            service.create_key(
                user_id=test_user_id,
                project_id=UUID(test_project_id),
                name=f"Key {i}",
            )

        # Try to create one more
        with pytest.raises(APIKeyLimitExceeded):
            service.create_key(
                user_id=test_user_id,
                project_id=UUID(test_project_id),
                name="Too Many",
            )

    def test_list_keys(self, service, test_user_id, test_project_id, clean_api_keys):
        """Test listing API keys."""
        # Create a few keys
        key1 = service.create_key(
            user_id=test_user_id,
            project_id=UUID(test_project_id),
            name="Key 1",
        )
        key2 = service.create_key(
            user_id=test_user_id,
            project_id=UUID(test_project_id),
            name="Key 2",
            expires_in_days=30,
        )

        # List keys
        result = service.list_keys(
            user_id=test_user_id,
            project_id=UUID(test_project_id),
        )

        assert result.count == 2
        assert result.limit == 4
        assert len(result.keys) == 2

        # Verify key data
        keys_by_name = {k.name: k for k in result.keys}
        assert "Key 1" in keys_by_name
        assert "Key 2" in keys_by_name

        # Check that full keys are not returned
        for key in result.keys:
            assert key.key_preview.endswith("***...***")

    def test_get_key(self, service, test_user_id, test_project_id, clean_api_keys):
        """Test getting a specific API key."""
        created = service.create_key(
            user_id=test_user_id,
            project_id=UUID(test_project_id),
            name="Test Key",
        )

        result = service.get_key(
            user_id=test_user_id,
            project_id=UUID(test_project_id),
            key_id=created.id,
        )

        assert result.id == created.id
        assert result.name == "Test Key"
        assert result.key_preview.endswith("***...***")

    def test_get_key_not_found(self, service, test_user_id, test_project_id):
        """Test getting non-existent key."""
        from uuid import uuid4

        with pytest.raises(APIKeyNotFound):
            service.get_key(
                user_id=test_user_id,
                project_id=UUID(test_project_id),
                key_id=uuid4(),
            )

    def test_revoke_key(self, service, test_user_id, test_project_id, clean_api_keys):
        """Test revoking an API key."""
        created = service.create_key(
            user_id=test_user_id,
            project_id=UUID(test_project_id),
            name="To Revoke",
        )

        # Revoke the key
        service.revoke_key(
            user_id=test_user_id,
            project_id=UUID(test_project_id),
            key_id=created.id,
        )

        # Key should no longer be listed
        result = service.list_keys(
            user_id=test_user_id,
            project_id=UUID(test_project_id),
        )
        assert result.count == 0

    def test_validate_key_valid(self, service, test_user_id, test_project_id, clean_api_keys):
        """Test validating a valid key."""
        created = service.create_key(
            user_id=test_user_id,
            project_id=UUID(test_project_id),
            name="Valid Key",
        )

        # Validate the key
        result = service.validate_key(created.key)

        assert result.valid is True
        assert result.user_id == test_user_id
        assert result.project_id == UUID(test_project_id)
        assert result.expired is False
        assert result.revoked is False

    def test_validate_key_invalid(self, service):
        """Test validating an invalid key."""
        result = service.validate_key("dkr_invalidkey123")

        assert result.valid is False
        assert result.user_id is None
        assert result.project_id is None

    def test_validate_key_revoked(self, service, test_user_id, test_project_id, clean_api_keys):
        """Test validating a revoked key."""
        created = service.create_key(
            user_id=test_user_id,
            project_id=UUID(test_project_id),
            name="To Revoke",
        )

        # Revoke the key
        service.revoke_key(
            user_id=test_user_id,
            project_id=UUID(test_project_id),
            key_id=created.id,
        )

        # Validate should return revoked
        result = service.validate_key(created.key)

        assert result.valid is False
        assert result.revoked is True