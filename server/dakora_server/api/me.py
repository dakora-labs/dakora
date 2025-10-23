"""User context API endpoints.

Provides endpoints for retrieving authenticated user information
and their default project context.
"""

from typing import Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.engine import Engine

from ..auth import get_auth_context, AuthContext
from ..config import settings
from ..core.database import (
    get_engine,
    get_connection,
    users_table,
    workspaces_table,
    projects_table,
)
from ..core.provisioning import get_or_create_workspace


router = APIRouter(prefix="/api/me", tags=["user"])


# Simple in-memory cache for user context (1 minute TTL)
# Short TTL to balance performance with data freshness
_user_context_cache: dict[str, tuple[datetime, "UserContextResponse"]] = {}
CACHE_TTL = timedelta(minutes=1)  # Reduced from 5 to 1 minute


def invalidate_user_context_cache(user_id: str) -> None:
    """Invalidate cache for a specific user.
    
    Call this when:
    - User profile is updated
    - User is added/removed from workspace
    - Project is renamed or deleted
    """
    if user_id in _user_context_cache:
        del _user_context_cache[user_id]
        print(f"🗑️ Cache invalidated for user {user_id[:8]}...")


class UserContextResponse(BaseModel):
    """User context including default project."""

    user_id: str
    email: str
    name: Optional[str]
    project_id: str
    project_slug: str
    project_name: str


@router.get("/context", response_model=UserContextResponse)
async def get_user_context(
    auth_ctx: AuthContext = Depends(get_auth_context),
    engine: Engine = Depends(get_engine),
    x_bypass_cache: Optional[str] = Header(None),
) -> UserContextResponse:
    """Get the authenticated user's default project.

    For MVP: Returns the user's default project (lazy provisioning if needed).
    URL structure: /project/{project_slug}/prompts

    Args:
        auth_ctx: Authentication context from JWT or API key
        engine: Global database engine
        x_bypass_cache: Set to "true" to bypass cache (for admin operations)

    Returns:
        UserContextResponse with project details

    Raises:
        HTTPException: 401 if not authenticated, 500 for database errors
    """
    # Handle no-auth mode (development): return default project without database lookup
    if auth_ctx.auth_method == "none" and not settings.auth_required:
        return UserContextResponse(
            user_id="default",
            email="dev@localhost",
            name="Development User",
            project_id="default",
            project_slug="default",
            project_name="Default Project",
        )
    
    # Check cache first (unless bypass requested)
    cache_key = auth_ctx.user_id
    if x_bypass_cache != "true" and cache_key in _user_context_cache:
        cached_time, cached_data = _user_context_cache[cache_key]
        if datetime.utcnow() - cached_time < CACHE_TTL:
            return cached_data
    
    with get_connection(engine) as conn:
        # Get user from database
        # For API key: user_id is database UUID
        # For JWT: user_id is clerk_user_id
        if auth_ctx.auth_method == "api_key":
            where_clause = users_table.c.id == auth_ctx.user_id
        else:
            where_clause = users_table.c.clerk_user_id == auth_ctx.user_id

        user_result = conn.execute(
            select(
                users_table.c.id,
                users_table.c.email,
                users_table.c.name,
                users_table.c.clerk_user_id,
            ).where(where_clause)
        ).fetchone()

        if not user_result:
            raise HTTPException(
                status_code=401, detail="User not found in database"
            )

        user_db_id, email, name, clerk_user_id = user_result

        # Get user's workspace
        workspace_result = conn.execute(
            select(workspaces_table.c.id).where(
                workspaces_table.c.owner_id == user_db_id
            )
        ).fetchone()

        if not workspace_result:
            # Lazy provisioning: create workspace and project on first access
            # DON'T cache this - user might refresh during onboarding
            workspace_id, project_id = get_or_create_workspace(
                engine, user_db_id, name, email
            )

            # Fetch the newly created project
            project_result = conn.execute(
                select(
                    projects_table.c.id,
                    projects_table.c.slug,
                    projects_table.c.name,
                ).where(projects_table.c.id == project_id)
            ).fetchone()
            
            # Return immediately without caching (new user)
            if project_result:
                project_id, project_slug, project_name = project_result
                return UserContextResponse(
                    user_id=clerk_user_id,
                    email=email,
                    name=name,
                    project_id=str(project_id),
                    project_slug=project_slug,
                    project_name=project_name,
                )
        else:
            workspace_id = workspace_result[0]

            # Get default project for this workspace
            project_result = conn.execute(
                select(
                    projects_table.c.id,
                    projects_table.c.slug,
                    projects_table.c.name,
                )
                .where(projects_table.c.workspace_id == workspace_id)
                .limit(1)
            ).fetchone()

            if not project_result:
                raise HTTPException(
                    status_code=500, detail="No project found for user"
                )

        project_id, project_slug, project_name = project_result

        result = UserContextResponse(
            user_id=clerk_user_id,
            email=email,
            name=name,
            project_id=str(project_id),
            project_slug=project_slug,
            project_name=project_name,
        )
        
        # Cache the result
        _user_context_cache[cache_key] = (datetime.utcnow(), result)
        
        return result