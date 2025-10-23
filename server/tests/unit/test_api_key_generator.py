"""Unit tests for API key generator."""

import pytest
from dakora_server.core.api_keys.generator import APIKeyGenerator


class TestAPIKeyGenerator:
    """Test API key generation and utilities."""

    def test_generate_key_format(self):
        """Test that generated keys have the correct format."""
        key, key_hash = APIKeyGenerator.generate()

        # Check key format
        assert key.startswith("dkr_"), "Key should start with dkr_ prefix"
        assert len(key) > 12, "Key should be longer than just the prefix"

        # Check hash format
        assert key_hash.startswith("$2b$"), "Hash should be bcrypt format"
        assert len(key_hash) == 60, "Bcrypt hash should be 60 characters"

    def test_generate_key_uniqueness(self):
        """Test that generated keys are unique."""
        key1, _ = APIKeyGenerator.generate()
        key2, _ = APIKeyGenerator.generate()

        assert key1 != key2, "Generated keys should be unique"

    def test_get_prefix(self):
        """Test prefix extraction from key."""
        key, _ = APIKeyGenerator.generate()
        prefix = APIKeyGenerator.get_prefix(key)

        # Prefix should be first 8 characters
        assert len(prefix) == 8, "Prefix should be 8 characters"
        assert prefix == key[:8], "Prefix should match first 8 chars"
        assert prefix.startswith("dkr_"), "Prefix should start with dkr_"

    def test_get_prefix_short_key(self):
        """Test prefix extraction with short key."""
        short_key = "dkr_123"
        prefix = APIKeyGenerator.get_prefix(short_key)

        assert prefix == short_key, "Short key should return full key as prefix"

    def test_mask_key(self):
        """Test key masking for display."""
        prefix = "dkr_1a2b"
        suffix = "3c4d"
        masked = APIKeyGenerator.mask_key(prefix, suffix)

        assert masked == "dkr_1a2b...3c4d", "Masked key should have correct format"
        assert "..." in masked, "Masked key should contain ellipsis"
        assert masked.startswith(prefix), "Masked key should start with prefix"
        assert masked.endswith(suffix), "Masked key should end with suffix"

    def test_verify_key_valid(self):
        """Test key verification with valid key."""
        key, key_hash = APIKeyGenerator.generate()

        # Should verify correctly
        assert APIKeyGenerator.verify_key(key, key_hash), "Valid key should verify"

    def test_verify_key_invalid(self):
        """Test key verification with invalid key."""
        key, key_hash = APIKeyGenerator.generate()
        wrong_key = "dkr_wrongkey123"

        # Should not verify
        assert not APIKeyGenerator.verify_key(wrong_key, key_hash), "Invalid key should not verify"

    def test_verify_key_different_keys(self):
        """Test that keys don't verify against each other's hashes."""
        key1, hash1 = APIKeyGenerator.generate()
        key2, hash2 = APIKeyGenerator.generate()

        # Keys should not cross-verify
        assert not APIKeyGenerator.verify_key(key1, hash2), "Key1 should not verify with hash2"
        assert not APIKeyGenerator.verify_key(key2, hash1), "Key2 should not verify with hash1"

    def test_key_prefix_uniqueness(self):
        """Test that key prefixes are reasonably unique."""
        prefixes = set()
        for _ in range(100):
            key, _ = APIKeyGenerator.generate()
            prefix = APIKeyGenerator.get_prefix(key)
            prefixes.add(prefix)

        # Should have high uniqueness (allow for small collision rate)
        assert len(prefixes) >= 95, "Should have high prefix uniqueness"