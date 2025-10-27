"""Project-scoped API routes."""

from typing import Any
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.engine import Engine
from sqlalchemy import select, func

from ..core.database import get_engine, get_connection, prompts_table
from ..auth import validate_project_access

router = APIRouter(prefix="/api/projects/{project_id}", tags=["projects"])


@router.get("/stats")
async def get_project_stats(
    project_id: UUID = Depends(validate_project_access),
    engine: Engine = Depends(get_engine),
) -> dict[str, Any]:
    """Get statistics for the project.

    Args:
        project_id: Validated project UUID
        engine: Database engine

    Returns:
        dict containing project statistics (prompt count, etc.)

    Raises:
        HTTPException: 500 if query fails
    """
    try:
        with get_connection(engine) as conn:
            # Count distinct prompts for this project
            stmt = select(func.count(func.distinct(prompts_table.c.prompt_id))).where(
                prompts_table.c.project_id == project_id
            )
            result = conn.execute(stmt)
            prompt_count = result.scalar() or 0

        return {
            "prompts_count": prompt_count,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch stats: {str(e)}")