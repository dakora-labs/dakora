"""Project-scoped API routes."""

from typing import Any, Optional
from uuid import UUID
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from sqlalchemy.engine import Engine
from sqlalchemy import select, func, and_, cast, Date

from ..core.database import (
    get_engine,
    get_connection,
    prompts_table,
    traces_table,
    executions_table,
    template_traces_table,
)
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
    days: int = Query(30, ge=1, le=365, description="Number of days for daily trend window"),
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
        - daily_costs: array of {date, cost} for the last `days` days (default 30)
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

            # Aggregate only chat executions — these are the spans that
            # carry model/tokens/cost information. Filter directly on the
            # executions table (it has project_id) to avoid an unnecessary join.
            # Total cost from chat spans with a computed cost
            cost_total_stmt = (
                select(func.coalesce(func.sum(executions_table.c.total_cost_usd), 0).label("total_cost"))
                .where(
                    and_(
                        executions_table.c.project_id == project_id,
                        executions_table.c.type == "chat",
                        executions_table.c.total_cost_usd.isnot(None),
                    )
                )
            )
            total_cost_row = conn.execute(cost_total_stmt).fetchone()
            total_cost = float(total_cost_row.total_cost) if total_cost_row else 0.0

            # Execution count = all chat spans (even when cost is null)
            exec_count_stmt = (
                select(func.count(func.distinct(executions_table.c.trace_id)).label("cnt")).where(
                    and_(
                        executions_table.c.project_id == project_id,
                        executions_table.c.type == "chat",
                    )
                )
            )
            total_executions = (conn.execute(exec_count_stmt).scalar() or 0)
            avg_cost = (total_cost / total_executions) if total_executions > 0 else 0.0

            # Get daily costs for last 30 days
            # DB-side zero-fill using generate_series for optimal performance
            # Define the date window [start_date, today], inclusive, for the requested days
            today_utc = datetime.now(timezone.utc).date()
            start_date = today_utc - timedelta(days=days - 1)

            # Aggregate costs by day within the window
            agg_subq = (
                select(
                    cast(executions_table.c.start_time, Date).label("day"),
                    func.coalesce(func.sum(executions_table.c.total_cost_usd), 0).label("cost"),
                )
                .where(
                    and_(
                        executions_table.c.project_id == project_id,
                        executions_table.c.type == "chat",
                        cast(executions_table.c.start_time, Date) >= start_date,
                        cast(executions_table.c.start_time, Date) <= today_utc,
                        executions_table.c.total_cost_usd.isnot(None),
                    )
                )
                .group_by(cast(executions_table.c.start_time, Date))
                .subquery("agg")
            )

            # Date series for the window (1-day step)
            date_series = (
                select(
                    cast(
                        func.generate_series(
                            start_date,
                            today_utc,
                            func.make_interval(0, 0, 0, 1),  # 1 day interval
                        ),
                        Date,
                    ).label("day")
                )
                .subquery("series")
            )

            daily_costs_stmt = (
                select(
                    date_series.c.day.label("date"),
                    func.coalesce(agg_subq.c.cost, 0).label("cost"),
                )
                .select_from(
                    date_series.outerjoin(agg_subq, date_series.c.day == agg_subq.c.day)
                )
                .order_by(date_series.c.day)
            )

            daily_costs_result = conn.execute(daily_costs_stmt).fetchall()
            daily_costs = [
                {"date": row.date.isoformat(), "cost": float(row.cost)} for row in daily_costs_result
            ]

            # Get top 5 prompts by total chat cost. Join template links → executions
            # by trace_id. We restrict to chat spans for accurate cost accounting.
            top_prompts_stmt = (
                select(
                    template_traces_table.c.prompt_id,
                    func.coalesce(func.sum(executions_table.c.total_cost_usd), 0).label("total_cost"),
                    func.count(func.distinct(executions_table.c.trace_id)).label("execution_count"),
                )
                .select_from(
                    template_traces_table.join(
                        executions_table,
                        template_traces_table.c.trace_id == executions_table.c.trace_id,
                    )
                )
                .where(
                    and_(
                        executions_table.c.project_id == project_id,
                        executions_table.c.type == "chat",
                        cast(executions_table.c.start_time, Date) >= start_date,
                        cast(executions_table.c.start_time, Date) <= today_utc,
                        executions_table.c.total_cost_usd.isnot(None),
                    )
                )
                .group_by(template_traces_table.c.prompt_id)
                .order_by(func.sum(executions_table.c.total_cost_usd).desc())
                .limit(5)
            )

            top_prompts_result = conn.execute(top_prompts_stmt).fetchall()
            top_prompts = [
                {
                    "prompt_id": row.prompt_id,
                    "name": row.prompt_id,  # Use prompt_id as name for now
                    "cost": float(row.total_cost),
                    "execution_count": row.execution_count,
                    "avg_cost": (float(row.total_cost) / row.execution_count) if row.execution_count else 0.0,
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
