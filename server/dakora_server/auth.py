"""Authentication and authorization for Dakora API.

This module provides FastAPI dependencies for authentication and scoped vault access.
Supports multiple authentication methods:
- API keys (hashed in database)
- Clerk JWT tokens
- No-auth mode (single-tenant)
"""

import jwt
from typing import Optional, cast
from uuid import UUID
from fastapi import Depends, Header, HTTPException, Path
from pydantic import BaseModel
from sqlalchemy import select

from .config import get_vault, settings
from .core.vault import Vault
from .core.registry import Registry
from .core.database import create_db_engine, get_connection, projects_table, workspaces_table, workspace_members_table, users_table


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

    # Create a new Vault with the scoped registry
    # Logger is shared across vaults and uses PostgreSQL (no db_path needed)
    return Vault(
        scoped_registry,
        logging_enabled=base_vault.logger is not None,
    )


async def validate_project_access(
    project_id: str = Path(..., description="Project ID or slug"),
    auth_ctx: AuthContext = Depends(get_auth_context),
) -> UUID:
    """Validate that the authenticated user has access to the project.

    For MVP: Auto-resolve to user's default project in development mode.
    For production: Validate workspace membership.

    Args:
        project_id: Project UUID or "default" slug from path parameter
        auth_ctx: Authentication context

    Returns:
        project_id UUID if access is granted

    Raises:
        HTTPException: 403 if user lacks access, 404 if project not found
    """
    # Handle no-auth mode with "default" project slug
    if auth_ctx.auth_method == "none" and project_id == "default":
        # Return a dummy UUID for the default project in no-auth mode
        # This allows the vault to use the project_id in storage paths
        from uuid import uuid5, NAMESPACE_DNS
        return uuid5(NAMESPACE_DNS, "default-project")
    
    # Try to parse as UUID
    try:
        project_uuid = UUID(project_id)
    except ValueError:
        raise HTTPException(
            status_code=422, 
            detail=f"Invalid project ID format. Expected UUID, got: {project_id}"
        )
    
    engine = create_db_engine()

    with get_connection(engine) as conn:
        # Check if project exists
        project_result = conn.execute(
            select(projects_table.c.id, projects_table.c.workspace_id).where(
                projects_table.c.id == project_uuid
            )
        ).fetchone()

        if not project_result:
            raise HTTPException(status_code=404, detail="Project not found")

        workspace_id = project_result[1]

        # In development mode (no auth), skip membership check
        if auth_ctx.auth_method == "none":
            return project_uuid

        # Get user from database using clerk_user_id
        user_result = conn.execute(
            select(users_table.c.id).where(
                users_table.c.clerk_user_id == auth_ctx.user_id
            )
        ).fetchone()

        if not user_result:
            raise HTTPException(status_code=403, detail="User not found")

        user_db_id = user_result[0]

        # Check workspace membership
        membership_result = conn.execute(
            select(workspace_members_table.c.role).where(
                workspace_members_table.c.workspace_id == workspace_id,
                workspace_members_table.c.user_id == user_db_id
            )
        ).fetchone()

        if not membership_result:
            raise HTTPException(
                status_code=403,
                detail="You do not have access to this project"
            )

        return project_uuid


def get_project_vault(
    project_id: UUID = Depends(validate_project_access),
    base_vault: Vault = Depends(get_vault),
) -> Vault:
    """Get a project-scoped vault instance.

    Creates a new Vault with a scoped registry that only accesses the project's
    storage prefix. This provides storage-level isolation at the project level.

    Args:
        project_id: Project UUID (validated by validate_project_access)
        base_vault: Base vault instance from get_vault

    Returns:
        Vault instance scoped to the project's storage prefix
    """
    # Create project-scoped storage prefix
    prefix = f"projects/{project_id}"

    # Create a scoped registry
    scoped_registry = cast(
        Registry,
        base_vault.registry.with_prefix(prefix)  # type: ignore[attr-defined]
    )

    # Create a new Vault with the scoped registry
    # Logger uses PostgreSQL (no db_path needed)
    return Vault(
        scoped_registry,
        logging_enabled=base_vault.logger is not None,
    )
