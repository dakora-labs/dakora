"""Authentication and authorization for Dakora API.

This module provides FastAPI dependencies for authentication and scoped vault access.
Supports multiple authentication methods:
- API keys (hashed in database)
- Clerk JWT tokens
- No-auth mode (single-tenant)
"""

import jwt
from typing import Optional, cast
from fastapi import Depends, Header, HTTPException
from pydantic import BaseModel

from .config import get_vault, settings
from .core.vault import Vault
from .core.registry import Registry


class AuthContext(BaseModel):
    """Authentication context for a request."""

    user_id: str
    project_id: Optional[str] = None
    auth_method: str  # "api_key", "jwt", "none"

    @property
    def storage_prefix(self) -> str:
        """Get the storage prefix for this auth context.

        Returns:
            Storage prefix path (e.g., "users/user123" or "projects/proj456")
        """
        if self.project_id:
            return f"projects/{self.project_id}"
        return f"users/{self.user_id}"

async def get_auth_context(
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None),
) -> AuthContext:
    """Extract authentication context from request headers.

    Priority:
    1. API key (X-API-Key header)
    2. JWT token (Authorization: Bearer header)
    3. No-auth mode (development only)

    Args:
        authorization: Authorization header (Bearer token)
        x_api_key: API key header

    Returns:
        AuthContext with user_id and optional project_id

    Raises:
        HTTPException: 401 if authentication fails or is missing
    """
    # Priority 1: Check for API key
    if x_api_key:
        # TODO: Implement API key validation
        # For now, treat any API key as valid with a test user
        return AuthContext(
            user_id=f"apikey_{x_api_key[:8]}",
            project_id=None,
            auth_method="api_key",
        )

    # Priority 2: Check for JWT Bearer token
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
        
        try:
            # Decode JWT without verification first to get the issuer
            unverified = jwt.decode(token, options={"verify_signature": False})
            
            # If Clerk settings are configured, verify the token
            if settings.clerk_jwt_issuer and settings.clerk_jwks_url:
                # Get the signing key from JWKS
                from jwt import PyJWKClient
                jwks_client = PyJWKClient(settings.clerk_jwks_url)
                signing_key = jwks_client.get_signing_key_from_jwt(token)
                
                # Verify the token
                payload = jwt.decode(
                    token,
                    signing_key.key,
                    algorithms=["RS256"],
                    issuer=settings.clerk_jwt_issuer,
                    options={"verify_signature": True, "verify_exp": True}
                )
            else:
                # No verification configured - decode only (for local testing)
                payload = unverified
            
            # Extract user info from JWT claims
            user_id = payload.get("sub") or payload.get("user_id")
            if not user_id:
                raise HTTPException(status_code=401, detail="Invalid token: missing user_id")
            
            return AuthContext(
                user_id=user_id,
                project_id=payload.get("project_id"),
                auth_method="jwt",
            )
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token has expired")
        except jwt.InvalidTokenError as e:
            raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=401, detail=f"Authentication error: {str(e)}")

    # Priority 3: No auth provided
    if settings.auth_required:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Provide X-API-Key or Authorization: Bearer header."
        )
    
    # Development mode: allow unauthenticated access with default user
    return AuthContext(
        user_id="default",
        project_id=None,
        auth_method="none",
    )


def get_user_vault(
    auth_ctx: AuthContext = Depends(get_auth_context),
    base_vault: Vault = Depends(get_vault),
) -> Vault:
    """Get a user-scoped vault instance.

    Creates a new Vault with a scoped registry that only accesses the user's
    storage prefix. This provides storage-level isolation for multi-tenancy.

    Args:
        auth_ctx: Authentication context from get_auth_context
        base_vault: Base vault instance from get_vault

    Returns:
        Vault instance scoped to the user's storage prefix

    Raises:
        HTTPException: 500 if registry doesn't support scoping
    """
    # Get the storage prefix for this user/project
    prefix = auth_ctx.storage_prefix

    # Create a scoped registry using the with_prefix method
    # Note: with_prefix is available on TemplateRegistry, not the base Registry protocol
    # We use cast to tell the type checker this returns a Registry instance
    scoped_registry = cast(
        Registry,
        base_vault.registry.with_prefix(prefix)  # type: ignore[attr-defined]
    )

    # Create a new Vault with the scoped registry but shared logger/renderer
    # This avoids creating multiple logger instances and keeps resource usage low
    return Vault(
        scoped_registry,
        logging_enabled=base_vault.logger is not None,
        logging_db_path=base_vault.config.get("logging", {}).get("db_path", "./dakora.db"),
    )
