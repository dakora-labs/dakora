"""Project-scoped API routes."""

from typing import Any, Optional
from uuid import UUID
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.engine import Engine
from sqlalchemy import select, func, and_, cast, Date

from ..core.database import get_engine, get_connection, prompts_table, traces_table
from ..core.budget import BudgetService
from ..auth import validate_project_access


class UpdateBudgetRequest(BaseModel):
    """Request model for updating budget settings."""

    budget_monthly_usd: Optional[float] = None
    alert_threshold_pct: Optional[int] = None
    enforcement_mode: Optional[str] = None

router = APIRouter(prefix="/api/projects/{project_id}", tags=["projects"])


@router.get("/stats")
async def get_project_stats(
    project_id: UUID = Depends(validate_project_access),
    engine: Engine = Depends(get_engine),
) -> dict[str, Any]:
    """Get statistics and analytics for the project.

    Args:
        project_id: Validated project UUID
        engine: Database engine

    Returns:
        dict containing project statistics including:
        - prompts_count: number of distinct prompts
        - total_cost: total execution cost in USD
        - total_executions: number of executions
        - avg_cost_per_execution: average cost per execution
        - daily_costs: array of {date, cost} for last 30 days
        - top_prompts: array of {prompt_id, name, cost, execution_count} for top 5 prompts by cost

    Raises:
        HTTPException: 500 if query fails
    """
    try:
        with get_connection(engine) as conn:
            # Count distinct prompts for this project
            prompt_count_stmt = select(func.count(func.distinct(prompts_table.c.prompt_id))).where(
                prompts_table.c.project_id == project_id
            )
            prompt_count = conn.execute(prompt_count_stmt).scalar() or 0

            # Get total cost and execution count
            cost_stats_stmt = select(
                func.coalesce(func.sum(traces_table.c.cost_usd), 0).label('total_cost'),
                func.count(traces_table.c.trace_id).label('total_executions')
            ).where(
                and_(
                    traces_table.c.project_id == project_id,
                    traces_table.c.cost_usd.isnot(None)
                )
            )
            cost_stats = conn.execute(cost_stats_stmt).fetchone()
            total_cost = float(cost_stats.total_cost) if cost_stats else 0.0
            total_executions = cost_stats.total_executions if cost_stats else 0
            avg_cost = (total_cost / total_executions) if total_executions > 0 else 0.0

            # Get daily costs for last 30 days
            thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
            daily_costs_stmt = select(
                cast(traces_table.c.created_at, Date).label('date'),
                func.coalesce(func.sum(traces_table.c.cost_usd), 0).label('cost')
            ).where(
                and_(
                    traces_table.c.project_id == project_id,
                    traces_table.c.created_at >= thirty_days_ago,
                    traces_table.c.cost_usd.isnot(None)
                )
            ).group_by(
                cast(traces_table.c.created_at, Date)
            ).order_by(
                cast(traces_table.c.created_at, Date)
            )
            daily_costs_result = conn.execute(daily_costs_stmt).fetchall()
            daily_costs = [
                {
                    "date": row.date.isoformat(),
                    "cost": float(row.cost)
                }
                for row in daily_costs_result
            ]

            # Get top 5 prompts by total cost
            top_prompts_stmt = select(
                traces_table.c.prompt_id,
                func.coalesce(func.sum(traces_table.c.cost_usd), 0).label('total_cost'),
                func.count(traces_table.c.trace_id).label('execution_count')
            ).where(
                and_(
                    traces_table.c.project_id == project_id,
                    traces_table.c.prompt_id.isnot(None),
                    traces_table.c.cost_usd.isnot(None)
                )
            ).group_by(
                traces_table.c.prompt_id
            ).order_by(
                func.sum(traces_table.c.cost_usd).desc()
            ).limit(5)

            top_prompts_result = conn.execute(top_prompts_stmt).fetchall()
            top_prompts = [
                {
                    "prompt_id": row.prompt_id,
                    "name": row.prompt_id,  # Use prompt_id as name for now
                    "cost": float(row.total_cost),
                    "execution_count": row.execution_count
                }
                for row in top_prompts_result
            ]

        return {
            "prompts_count": prompt_count,
            "total_cost": round(total_cost, 2),
            "total_executions": total_executions,
            "avg_cost_per_execution": round(avg_cost, 4),
            "daily_costs": daily_costs,
            "top_prompts": top_prompts,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch stats: {str(e)}")


@router.get("/budget")
async def get_budget(
    project_id: UUID = Depends(validate_project_access),
    engine: Engine = Depends(get_engine),
) -> dict[str, Any]:
    """Get project budget status with current spend.

    Args:
        project_id: Validated project UUID
        engine: Database engine

    Returns:
        dict containing budget status and current spend

    Raises:
        HTTPException: 404 if project not found, 500 if query fails
    """
    try:
        budget_service = BudgetService(engine)
        return budget_service.check_budget_status(project_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch budget: {str(e)}")


@router.put("/budget")
async def update_budget(
    request: UpdateBudgetRequest,
    project_id: UUID = Depends(validate_project_access),
    engine: Engine = Depends(get_engine),
) -> dict[str, Any]:
    """Update project budget settings.

    Args:
        request: Budget update request
        project_id: Validated project UUID
        engine: Database engine

    Returns:
        dict containing updated budget status

    Raises:
        HTTPException: 400 if validation fails, 500 if update fails
    """
    try:
        budget_service = BudgetService(engine)
        return budget_service.update_budget(
            project_id=project_id,
            budget_monthly_usd=request.budget_monthly_usd,
            alert_threshold_pct=request.alert_threshold_pct,
            enforcement_mode=request.enforcement_mode,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update budget: {str(e)}")