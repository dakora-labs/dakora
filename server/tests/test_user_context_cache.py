"""Tests for user context caching and invalidation.

Tests cover:
- Cache TTL constants
- Cache invalidation function
- Multiple user cache isolation

Note: These tests verify cache behavior in isolation using the
invalidate_user_context_cache function and direct cache access.
Full integration tests with the API endpoint are in test_auth.py
and test_webhook_provisioning.py
"""

import pytest
from datetime import datetime, timedelta
from dakora_server.api.me import (
    _user_context_cache,
    CACHE_TTL,
    invalidate_user_context_cache,
    UserContextResponse,
)


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear the cache before and after each test."""
    _user_context_cache.clear()
    yield
    _user_context_cache.clear()


class TestCacheInvalidation:
    """Tests for cache invalidation functionality."""

    def test_invalidate_user_context_cache(self):
        """Test manual cache invalidation."""
        user_id = "test_user_invalidate"
        
        # Pre-populate cache with a UserContextResponse object
        cached_response = UserContextResponse(
            user_id=user_id,
            email="test@example.com",
            name="Test User",
            project_id="proj_123",
            project_slug="test-project",
            project_name="Test Project",
        )
        _user_context_cache[user_id] = (datetime.utcnow(), cached_response)
        
        # Verify cache exists
        assert user_id in _user_context_cache
        
        # Invalidate cache
        invalidate_user_context_cache(user_id)
        
        # Verify cache is cleared
        assert user_id not in _user_context_cache

    def test_invalidate_nonexistent_user(self):
        """Test invalidating cache for user that doesn't exist."""
        user_id = "nonexistent_user"
        
        # Verify cache is empty
        assert user_id not in _user_context_cache
        
        # Should not raise error
        invalidate_user_context_cache(user_id)
        
        # Still empty
        assert user_id not in _user_context_cache

    def test_multiple_users_isolated_cache(self):
        """Test that different users have isolated cache entries."""
        user1_id = "user_1"
        user2_id = "user_2"
        
        # Pre-populate cache for user 1
        response1 = UserContextResponse(
            user_id=user1_id,
            email="user1@example.com",
            name="User One",
            project_id="proj1",
            project_slug="project-1",
            project_name="Project One",
        )
        _user_context_cache[user1_id] = (datetime.utcnow(), response1)
        
        # Pre-populate cache for user 2
        response2 = UserContextResponse(
            user_id=user2_id,
            email="user2@example.com",
            name="User Two",
            project_id="proj2",
            project_slug="project-2",
            project_name="Project Two",
        )
        _user_context_cache[user2_id] = (datetime.utcnow(), response2)
        
        # Verify both users cached
        assert user1_id in _user_context_cache
        assert user2_id in _user_context_cache
        
        # Verify cache data is different
        _, data1 = _user_context_cache[user1_id]
        _, data2 = _user_context_cache[user2_id]
        assert data1.email != data2.email
        assert data1.project_slug != data2.project_slug
        
        # Invalidate user 1
        invalidate_user_context_cache(user1_id)
        
        # Verify only user 1 is cleared
        assert user1_id not in _user_context_cache
        assert user2_id in _user_context_cache


class TestCacheTTL:
    """Tests for cache TTL behavior."""

    def test_cache_ttl_constant(self):
        """Test that CACHE_TTL is set correctly."""
        assert CACHE_TTL == timedelta(minutes=1)

    def test_cache_within_ttl(self):
        """Test that cache within TTL is recent."""
        user_id = "test_user_ttl"
        cached_time = datetime.utcnow() - timedelta(seconds=30)  # 30 seconds ago
        
        cached_response = UserContextResponse(
            user_id=user_id,
            email="test@example.com",
            name="Test User",
            project_id="proj_123",
            project_slug="test-project",
            project_name="Test Project",
        )
        _user_context_cache[user_id] = (cached_time, cached_response)
        
        # Verify time difference is less than TTL
        time_diff = datetime.utcnow() - cached_time
        assert time_diff < CACHE_TTL

    def test_cache_beyond_ttl(self):
        """Test that cache beyond TTL is expired."""
        user_id = "test_user_expired"
        cached_time = datetime.utcnow() - CACHE_TTL - timedelta(seconds=10)
        
        cached_response = UserContextResponse(
            user_id=user_id,
            email="test@example.com",
            name="Test User",
            project_id="proj_123",
            project_slug="test-project",
            project_name="Test Project",
        )
        _user_context_cache[user_id] = (cached_time, cached_response)
        
        # Verify time difference exceeds TTL
        time_diff = datetime.utcnow() - cached_time
        assert time_diff > CACHE_TTL


class TestCacheStorage:
    """Tests for cache storage behavior."""

    def test_cache_stores_correct_structure(self):
        """Test that cache stores (timestamp, UserContextResponse) tuple."""
        user_id = "test_structure"
        
        cached_response = UserContextResponse(
            user_id=user_id,
            email="test@example.com",
            name="Test User",
            project_id="proj_123",
            project_slug="test-project",
            project_name="Test Project",
        )
        timestamp = datetime.utcnow()
        _user_context_cache[user_id] = (timestamp, cached_response)
        
        # Retrieve from cache
        cached_tuple = _user_context_cache[user_id]
        
        # Verify structure
        assert isinstance(cached_tuple, tuple)
        assert len(cached_tuple) == 2
        assert isinstance(cached_tuple[0], datetime)
        assert isinstance(cached_tuple[1], UserContextResponse)
        
        # Verify data
        cached_time, cached_data = cached_tuple
        assert cached_data.user_id == user_id
        assert cached_data.email == "test@example.com"
        assert cached_data.project_slug == "test-project"

    def test_cache_can_store_multiple_users(self):
        """Test that cache can hold multiple users simultaneously."""
        users = [
            ("user_1", "user1@example.com", "project-1"),
            ("user_2", "user2@example.com", "project-2"),
            ("user_3", "user3@example.com", "project-3"),
        ]
        
        # Populate cache with multiple users
        for user_id, email, slug in users:
            response = UserContextResponse(
                user_id=user_id,
                email=email,
                name=f"User {user_id}",
                project_id=f"proj_{user_id}",
                project_slug=slug,
                project_name=f"Project {user_id}",
            )
            _user_context_cache[user_id] = (datetime.utcnow(), response)
        
        # Verify all are cached
        assert len(_user_context_cache) == 3
        for user_id, _, _ in users:
            assert user_id in _user_context_cache

    def test_cache_overwrites_existing_entry(self):
        """Test that setting cache for same user overwrites previous entry."""
        user_id = "test_overwrite"
        
        # First entry
        response1 = UserContextResponse(
            user_id=user_id,
            email="old@example.com",
            name="Old Name",
            project_id="old_proj",
            project_slug="old-project",
            project_name="Old Project",
        )
        _user_context_cache[user_id] = (datetime.utcnow(), response1)
        
        # Verify first entry
        _, cached = _user_context_cache[user_id]
        assert cached.email == "old@example.com"
        
        # Second entry (overwrite)
        response2 = UserContextResponse(
            user_id=user_id,
            email="new@example.com",
            name="New Name",
            project_id="new_proj",
            project_slug="new-project",
            project_name="New Project",
        )
        _user_context_cache[user_id] = (datetime.utcnow(), response2)
        
        # Verify overwrite
        _, cached = _user_context_cache[user_id]
        assert cached.email == "new@example.com"
        assert cached.project_slug == "new-project"

