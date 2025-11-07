"""User feedback API endpoints."""

from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import insert, select
from sqlalchemy.engine import Engine

from ..auth import get_auth_context, AuthContext
from ..core.database import get_engine, get_connection, user_feedback_table, users_table
from .schemas import FeedbackRequest, FeedbackResponse


router = APIRouter(prefix="/api", tags=["feedback"])


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    request: FeedbackRequest,
    auth_ctx: AuthContext = Depends(get_auth_context),
    engine: Engine = Depends(get_engine),
) -> FeedbackResponse:
    """Submit user feedback.

    Stores user feedback with rating and optional text comment.
    Captures user information from authentication context.

    Args:
        request: Feedback submission with rating and optional text
        auth_ctx: Authentication context from JWT or API key
        engine: Global database engine

    Returns:
        FeedbackResponse with feedback ID and creation timestamp

    Raises:
        HTTPException: 400 for invalid data, 500 for database errors
    """
    try:
        with get_connection(engine) as conn:
            # Get user information
            user_stmt = select(users_table.c.id, users_table.c.email, users_table.c.name).where(
                users_table.c.clerk_user_id == auth_ctx.user_id
            )
            user_result = conn.execute(user_stmt).first()

            if not user_result:
                raise HTTPException(status_code=404, detail="User not found")

            user_uuid: UUID = user_result.id
            user_email: str = user_result.email
            user_name: str | None = user_result.name

            # Get project_id and workspace_id from auth context if available
            project_id: UUID | None = auth_ctx.project_id if hasattr(auth_ctx, "project_id") else None
            workspace_id: UUID | None = auth_ctx.workspace_id if hasattr(auth_ctx, "workspace_id") else None

            # Insert feedback
            insert_stmt = insert(user_feedback_table).values(
                user_id=user_uuid,
                project_id=project_id,
                workspace_id=workspace_id,
                rating=request.rating,
                feedback=request.feedback,
                user_email=user_email,
                user_name=user_name,
            ).returning(
                user_feedback_table.c.id,
                user_feedback_table.c.created_at,
            )

            result = conn.execute(insert_stmt).first()

            if not result:
                raise HTTPException(status_code=500, detail="Failed to save feedback")

            feedback_id: UUID = result.id
            created_at: datetime = result.created_at

            return FeedbackResponse(
                id=str(feedback_id),
                created_at=created_at.isoformat(),
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving feedback: {str(e)}")