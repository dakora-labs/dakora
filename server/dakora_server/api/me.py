"""User context API endpoints.

Provides endpoints for retrieving authenticated user information
and their default project context.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from ..auth import get_auth_context, AuthContext
from ..core.database import (
    create_db_engine,
    get_connection,
    users_table,
    workspaces_table,
    projects_table,
)
from ..core.provisioning import get_or_create_workspace


router = APIRouter(prefix="/api/me", tags=["user"])


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
) -> UserContextResponse:
    """Get the authenticated user's default project.

    For MVP: Returns the user's default project (lazy provisioning if needed).
    URL structure: /project/{project_slug}/prompts

    Args:
        auth_ctx: Authentication context from JWT or API key

    Returns:
        UserContextResponse with project details

    Raises:
        HTTPException: 401 if not authenticated, 500 for database errors
    """
    engine = create_db_engine()

    with get_connection(engine) as conn:
        # Get user from database using clerk_user_id
        user_result = conn.execute(
            select(
                users_table.c.id,
                users_table.c.email,
                users_table.c.name,
                users_table.c.clerk_user_id,
            ).where(users_table.c.clerk_user_id == auth_ctx.user_id)
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

        return UserContextResponse(
            user_id=clerk_user_id,
            email=email,
            name=name,
            project_id=str(project_id),
            project_slug=project_slug,
            project_name=project_name,
        )