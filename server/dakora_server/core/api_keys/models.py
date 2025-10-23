"""Pydantic models for API keys."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class APIKeyCreate(BaseModel):
    """Request model for creating an API key."""

    name: Optional[str] = Field(None, max_length=255, description="Optional name/label for the key")
    expires_in_days: Optional[int] = Field(
        None,
        description="Expiration period in days (30, 90, 365, or null for never)"
    )

    def validate_expiration(self) -> None:
        """Validate that expires_in_days is one of the allowed values."""
        if self.expires_in_days is not None and self.expires_in_days not in [30, 90, 365]:
            raise ValueError("expires_in_days must be one of: 30, 90, 365, or null")


class APIKey(BaseModel):
    """Database model for API key (internal use)."""

    id: UUID
    user_id: UUID
    project_id: UUID
    name: Optional[str]
    key_prefix: str
    key_hash: str
    created_at: datetime
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]
    revoked_at: Optional[datetime]


class APIKeyResponse(BaseModel):
    """Response model for API key operations."""

    id: UUID
    name: Optional[str]
    key_preview: str = Field(..., description="Masked key display (e.g., dkr_1a2b***...***)")
    created_at: datetime
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]


class APIKeyCreateResponse(BaseModel):
    """Response model for key creation (includes full key once)."""

    id: UUID
    name: Optional[str]
    key: str = Field(..., description="Full API key (shown only once)")
    key_prefix: str
    created_at: datetime
    expires_at: Optional[datetime]


class APIKeyListResponse(BaseModel):
    """Response model for listing API keys."""

    keys: list[APIKeyResponse]
    count: int = Field(..., description="Current number of keys")
    limit: int = Field(4, description="Maximum allowed keys per project")


class APIKeyValidationResult(BaseModel):
    """Result of API key validation."""

    valid: bool
    user_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    key_id: Optional[UUID] = None
    expired: bool = False
    revoked: bool = False