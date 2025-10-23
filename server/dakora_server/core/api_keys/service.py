"""API key service for business logic."""

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import select, insert, update, delete, and_, func
from sqlalchemy.engine import Engine

from dakora_server.core.database import api_keys_table, get_connection
from dakora_server.core.exceptions import DakoraError
from .generator import APIKeyGenerator
from .models import (
    APIKey,
    APIKeyCreate,
    APIKeyCreateResponse,
    APIKeyResponse,
    APIKeyListResponse,
    APIKeyValidationResult,
)


class APIKeyLimitExceeded(DakoraError):
    """Raised when project exceeds maximum API keys."""
    pass


class InvalidExpiration(DakoraError):
    """Raised when invalid expiration period is provided."""
    pass


class APIKeyNotFound(DakoraError):
    """Raised when API key is not found."""
    pass


class APIKeyService:
    """Service for managing API keys."""

    MAX_KEYS_PER_PROJECT = 4
    VALID_EXPIRATIONS = [30, 90, 365, None]

    def __init__(self, engine: Engine):
        """
        Initialize API key service.

        Args:
            engine: SQLAlchemy engine instance
        """
        self.engine = engine

    def create_key(
        self,
        user_id: UUID,
        project_id: UUID,
        name: Optional[str] = None,
        expires_in_days: Optional[int] = None,
    ) -> APIKeyCreateResponse:
        """
        Generate new API key.

        Args:
            user_id: User creating the key
            project_id: Project the key belongs to
            name: Optional name/label for the key
            expires_in_days: Expiration period (30, 90, 365, or None)

        Returns:
            APIKeyCreateResponse with full key (shown once)

        Raises:
            APIKeyLimitExceeded: If project has maximum keys
            InvalidExpiration: If expires_in_days is invalid
        """
        # Validate expiration
        if expires_in_days is not None and expires_in_days not in [30, 90, 365]:
            raise InvalidExpiration(
                "expires_in_days must be one of: 30, 90, 365, or null"
            )

        with get_connection(self.engine) as conn:
            # Check current key count
            count_query = select(func.count()).select_from(api_keys_table).where(
                and_(
                    api_keys_table.c.project_id == project_id,
                    api_keys_table.c.revoked_at.is_(None),
                )
            )
            current_count = conn.execute(count_query).scalar()

            if current_count >= self.MAX_KEYS_PER_PROJECT:
                raise APIKeyLimitExceeded(
                    f"Maximum {self.MAX_KEYS_PER_PROJECT} API keys per project. "
                    "Revoke an existing key to create a new one."
                )

            # Generate key
            full_key, key_hash = APIKeyGenerator.generate()
            key_prefix = APIKeyGenerator.get_prefix(full_key)
            key_suffix = APIKeyGenerator.get_suffix(full_key)

            # Calculate expiration
            expires_at = None
            if expires_in_days is not None:
                expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

            # Insert key
            insert_stmt = insert(api_keys_table).values(
                user_id=user_id,
                project_id=project_id,
                name=name,
                key_prefix=key_prefix,
                key_suffix=key_suffix,
                key_hash=key_hash,
                expires_at=expires_at,
            ).returning(
                api_keys_table.c.id,
                api_keys_table.c.created_at,
            )

            result = conn.execute(insert_stmt)
            row = result.fetchone()

            return APIKeyCreateResponse(
                id=row[0],
                name=name,
                key=full_key,
                key_prefix=key_prefix,
                created_at=row[1],
                expires_at=expires_at,
            )

    def list_keys(
        self,
        user_id: UUID,
        project_id: UUID,
    ) -> APIKeyListResponse:
        """
        List all active API keys for a project.

        Args:
            user_id: User requesting the list
            project_id: Project to list keys for

        Returns:
            APIKeyListResponse with masked keys
        """
        with get_connection(self.engine) as conn:
            # Get all non-revoked keys
            query = select(
                api_keys_table.c.id,
                api_keys_table.c.name,
                api_keys_table.c.key_prefix,
                api_keys_table.c.key_suffix,
                api_keys_table.c.created_at,
                api_keys_table.c.last_used_at,
                api_keys_table.c.expires_at,
            ).where(
                and_(
                    api_keys_table.c.project_id == project_id,
                    api_keys_table.c.revoked_at.is_(None),
                )
            ).order_by(api_keys_table.c.created_at.desc())

            result = conn.execute(query)
            rows = result.fetchall()

            keys = [
                APIKeyResponse(
                    id=row[0],
                    name=row[1],
                    key_preview=APIKeyGenerator.mask_key(row[2], row[3]),
                    created_at=row[4],
                    last_used_at=row[5],
                    expires_at=row[6],
                )
                for row in rows
            ]

            return APIKeyListResponse(
                keys=keys,
                count=len(keys),
                limit=self.MAX_KEYS_PER_PROJECT,
            )

    def get_key(
        self,
        user_id: UUID,
        project_id: UUID,
        key_id: UUID,
    ) -> APIKeyResponse:
        """
        Get details of a specific API key.

        Args:
            user_id: User requesting the key
            project_id: Project the key belongs to
            key_id: ID of the key

        Returns:
            APIKeyResponse with masked key

        Raises:
            APIKeyNotFound: If key doesn't exist or user doesn't have access
        """
        with get_connection(self.engine) as conn:
            query = select(
                api_keys_table.c.id,
                api_keys_table.c.name,
                api_keys_table.c.key_prefix,
                api_keys_table.c.key_suffix,
                api_keys_table.c.created_at,
                api_keys_table.c.last_used_at,
                api_keys_table.c.expires_at,
            ).where(
                and_(
                    api_keys_table.c.id == key_id,
                    api_keys_table.c.project_id == project_id,
                    api_keys_table.c.revoked_at.is_(None),
                )
            )

            result = conn.execute(query)
            row = result.fetchone()

            if not row:
                raise APIKeyNotFound("API key not found")

            return APIKeyResponse(
                id=row[0],
                name=row[1],
                key_preview=APIKeyGenerator.mask_key(row[2], row[3]),
                created_at=row[4],
                last_used_at=row[5],
                expires_at=row[6],
            )

    def revoke_key(
        self,
        user_id: UUID,
        project_id: UUID,
        key_id: UUID,
    ) -> None:
        """
        Revoke an API key.

        Args:
            user_id: User revoking the key
            project_id: Project the key belongs to
            key_id: ID of the key to revoke

        Raises:
            APIKeyNotFound: If key doesn't exist or user doesn't have access
        """
        with get_connection(self.engine) as conn:
            # Mark as revoked
            update_stmt = update(api_keys_table).where(
                and_(
                    api_keys_table.c.id == key_id,
                    api_keys_table.c.project_id == project_id,
                    api_keys_table.c.revoked_at.is_(None),
                )
            ).values(revoked_at=datetime.utcnow())

            result = conn.execute(update_stmt)

            if result.rowcount == 0:
                raise APIKeyNotFound("API key not found")

    def validate_key(self, key: str) -> APIKeyValidationResult:
        """
        Validate API key and return metadata.

        This method performs database lookup and hash comparison.
        For performance-critical paths, use APIKeyValidator with caching.

        Args:
            key: Full API key to validate

        Returns:
            APIKeyValidationResult with validation status and metadata
        """
        # Extract prefix for faster lookup
        key_prefix = APIKeyGenerator.get_prefix(key)

        with get_connection(self.engine) as conn:
            # Find keys with matching prefix
            query = select(
                api_keys_table.c.id,
                api_keys_table.c.user_id,
                api_keys_table.c.project_id,
                api_keys_table.c.key_hash,
                api_keys_table.c.expires_at,
                api_keys_table.c.revoked_at,
            ).where(
                api_keys_table.c.key_prefix == key_prefix
            )

            result = conn.execute(query)
            rows = result.fetchall()

            # Check each candidate key
            for row in rows:
                key_id, user_id, project_id, key_hash, expires_at, revoked_at = row

                # Verify hash
                if not APIKeyGenerator.verify_key(key, key_hash):
                    continue

                # Check if revoked
                if revoked_at is not None:
                    return APIKeyValidationResult(
                        valid=False,
                        revoked=True,
                    )

                # Check if expired
                if expires_at is not None and datetime.utcnow() > expires_at:
                    return APIKeyValidationResult(
                        valid=False,
                        expired=True,
                    )

                # Update last used timestamp
                update_stmt = update(api_keys_table).where(
                    api_keys_table.c.id == key_id
                ).values(last_used_at=datetime.utcnow())
                conn.execute(update_stmt)

                return APIKeyValidationResult(
                    valid=True,
                    user_id=user_id,
                    project_id=project_id,
                    key_id=key_id,
                )

            # No matching key found
            return APIKeyValidationResult(valid=False)