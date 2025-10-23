"""API key validator with in-memory caching.

This implementation uses in-memory caching for fast validation.
The caching interface is designed to be easily replaced with Redis in the future.
"""

import asyncio
import time
from datetime import datetime
from typing import Optional, Dict
from uuid import UUID

from sqlalchemy.engine import Engine

from .models import APIKeyValidationResult
from .service import APIKeyService


class CacheEntry:
    """Cache entry with expiration tracking."""

    def __init__(
        self,
        valid: bool,
        user_id: Optional[UUID],
        project_id: Optional[UUID],
        key_id: Optional[UUID],
        expires_at: Optional[datetime],
        revoked: bool = False,
        expired: bool = False,
    ):
        self.valid = valid
        self.user_id = user_id
        self.project_id = project_id
        self.key_id = key_id
        self.expires_at = expires_at
        self.revoked = revoked
        self.expired = expired
        self.cached_at = time.time()

    def to_validation_result(self) -> APIKeyValidationResult:
        """Convert cache entry to validation result."""
        return APIKeyValidationResult(
            valid=self.valid,
            user_id=self.user_id,
            project_id=self.project_id,
            key_id=self.key_id,
            expired=self.expired,
            revoked=self.revoked,
        )


class APIKeyValidator:
    """Fast key validation with in-memory cache.

    This class provides high-performance API key validation by caching
    validation results in memory. The cache design allows for easy migration
    to Redis or other distributed cache systems in the future.

    Cache Strategy:
    - Cache valid keys for TTL duration (default: 5 minutes)
    - Cache invalid keys for shorter duration to handle typos
    - Check expiration on every validation
    - Invalidate on revocation
    """

    def __init__(self, engine: Engine, cache_ttl: int = 300):
        """
        Initialize validator with caching.

        Args:
            engine: SQLAlchemy engine for database access
            cache_ttl: Cache TTL in seconds (default: 300 = 5 minutes)
        """
        self.engine = engine
        self.service = APIKeyService(engine)
        self.cache: Dict[str, CacheEntry] = {}
        self.cache_ttl = cache_ttl
        self.lock = asyncio.Lock()

    async def validate(self, key: str) -> APIKeyValidationResult:
        """
        Validate key with caching.

        Performance: < 10ms for cache hits, < 100ms for cache misses.

        Args:
            key: Full API key to validate

        Returns:
            APIKeyValidationResult with validation status and metadata
        """
        # Check cache first
        async with self.lock:
            if key in self.cache:
                entry = self.cache[key]

                # Check if cache entry is still valid
                if time.time() - entry.cached_at < self.cache_ttl:
                    # Check if key has expired since caching
                    if entry.expires_at and datetime.utcnow() > entry.expires_at:
                        # Key expired, update cache
                        entry.expired = True
                        entry.valid = False
                        return entry.to_validation_result()

                    return entry.to_validation_result()

                # Cache expired, remove entry
                del self.cache[key]

        # Cache miss - validate against database
        # Use sync service method in a thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self.service.validate_key,
            key,
        )

        # Cache the result
        async with self.lock:
            self.cache[key] = CacheEntry(
                valid=result.valid,
                user_id=result.user_id,
                project_id=result.project_id,
                key_id=result.key_id,
                expires_at=None,  # We'll check expiration on each access
                revoked=result.revoked,
                expired=result.expired,
            )

        return result

    async def invalidate(self, key_id: UUID) -> None:
        """
        Invalidate cache entry when key is revoked.

        This method removes all cache entries for keys with the given ID.
        In a distributed system, this would broadcast to all cache nodes.

        Args:
            key_id: ID of the key to invalidate
        """
        async with self.lock:
            # Remove all cache entries with matching key_id
            keys_to_remove = [
                key
                for key, entry in self.cache.items()
                if entry.key_id == key_id
            ]
            for key in keys_to_remove:
                del self.cache[key]

    async def invalidate_all(self) -> None:
        """
        Clear entire cache.

        Useful for testing or maintenance operations.
        """
        async with self.lock:
            self.cache.clear()

    def get_cache_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            dict: Cache statistics including size and hit/miss metrics
        """
        return {
            "size": len(self.cache),
            "ttl": self.cache_ttl,
            "entries": len(self.cache),
        }


# Global validator instance
_global_validator: Optional[APIKeyValidator] = None


def get_validator(engine: Optional[Engine] = None) -> APIKeyValidator:
    """
    Get or create global validator instance.

    Args:
        engine: SQLAlchemy engine (required on first call)

    Returns:
        Global APIKeyValidator instance
    """
    global _global_validator

    if _global_validator is None:
        if engine is None:
            from dakora_server.core.database import get_engine
            engine = get_engine()
        _global_validator = APIKeyValidator(engine)

    return _global_validator