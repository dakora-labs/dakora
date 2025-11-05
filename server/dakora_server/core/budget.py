"""Project budget tracking and enforcement service."""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select, update
from sqlalchemy.engine import Engine

from dakora_server.core.database import get_connection, projects_table, traces_table, executions_table


class BudgetService:
    """Manages project budget tracking and enforcement."""

    def __init__(self, engine: Engine):
        self.engine = engine

    def get_current_month_spend(self, project_id: UUID) -> float:
        """
        Calculate total spend for current calendar month.

        Uses indexed query: (project_id, created_at, cost_usd)

        Args:
            project_id: Project UUID

        Returns:
            Total spend in USD for current month
        """
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        with get_connection(self.engine) as conn:
            # Cost is stored in executions.total_cost_usd in the new schema
            # Join traces -> executions to get costs
            result = conn.execute(
                select(func.coalesce(func.sum(executions_table.c.total_cost_usd), 0)).select_from(
                    traces_table.join(
                        executions_table,
                        traces_table.c.trace_id == executions_table.c.trace_id
                    )
                ).where(
                    and_(
                        traces_table.c.project_id == project_id,
                        executions_table.c.created_at >= month_start,
                        executions_table.c.total_cost_usd.isnot(None),
                    )
                )
            )
            return float(result.scalar_one() or 0.0)

    def check_budget_status(self, project_id: UUID) -> dict[str, Any]:
        """
        Check budget status for middleware consumption.

        Returns fast response optimized for high-frequency calls.

        Args:
            project_id: Project UUID

        Returns:
            Budget status dictionary with keys:
                - exceeded: bool - whether budget is exceeded
                - budget_usd: float | None - monthly budget limit
                - current_spend_usd: float - current month spend
                - percentage_used: float - percentage of budget used
                - alert_threshold_pct: int - warning threshold percentage
                - enforcement_mode: str - enforcement mode (strict/alert/off)
                - status: str - status (unlimited/ok/warning/exceeded)
        """
        with get_connection(self.engine) as conn:
            # Get project budget settings
            result = conn.execute(
                select(
                    projects_table.c.budget_monthly_usd,
                    projects_table.c.alert_threshold_pct,
                    projects_table.c.budget_enforcement_mode,
                ).where(projects_table.c.id == project_id)
            )
            row = result.fetchone()

            if not row:
                raise ValueError(f"Project {project_id} not found")

            budget_usd = row.budget_monthly_usd
            alert_threshold_pct = row.alert_threshold_pct or 80
            enforcement_mode = row.budget_enforcement_mode or "strict"

            # No budget set = unlimited
            if budget_usd is None:
                return {
                    "exceeded": False,
                    "budget_usd": None,
                    "current_spend_usd": 0.0,
                    "percentage_used": 0.0,
                    "alert_threshold_pct": alert_threshold_pct,
                    "enforcement_mode": enforcement_mode,
                    "status": "unlimited",
                }

            # Calculate current spend
            current_spend = self.get_current_month_spend(project_id)
            percentage_used = (current_spend / float(budget_usd) * 100) if budget_usd > 0 else 0

            # Determine status
            exceeded = current_spend >= float(budget_usd)
            at_warning = percentage_used >= alert_threshold_pct

            if exceeded:
                status = "exceeded"
            elif at_warning:
                status = "warning"
            else:
                status = "ok"

            return {
                "exceeded": exceeded,
                "budget_usd": float(budget_usd),
                "current_spend_usd": current_spend,
                "percentage_used": round(percentage_used, 2),
                "alert_threshold_pct": alert_threshold_pct,
                "enforcement_mode": enforcement_mode,
                "status": status,
            }

    def update_budget(
        self,
        project_id: UUID,
        budget_monthly_usd: float | None = None,
        alert_threshold_pct: int | None = None,
        enforcement_mode: str | None = None,
    ) -> dict[str, Any]:
        """
        Update project budget settings.

        Args:
            project_id: Project UUID
            budget_monthly_usd: Monthly budget in USD (None = unlimited)
            alert_threshold_pct: Warning threshold percentage (0-100)
            enforcement_mode: Enforcement mode (strict/alert/off)

        Returns:
            Updated budget status

        Raises:
            ValueError: If validation fails
        """
        with get_connection(self.engine) as conn:
            update_values: dict[str, Any] = {}

            if budget_monthly_usd is not None:
                update_values["budget_monthly_usd"] = budget_monthly_usd
            if alert_threshold_pct is not None:
                if not 0 <= alert_threshold_pct <= 100:
                    raise ValueError("alert_threshold_pct must be between 0 and 100")
                update_values["alert_threshold_pct"] = alert_threshold_pct
            if enforcement_mode is not None:
                if enforcement_mode not in ("strict", "alert", "off"):
                    raise ValueError("enforcement_mode must be: strict, alert, or off")
                update_values["budget_enforcement_mode"] = enforcement_mode

            if update_values:
                conn.execute(
                    update(projects_table).where(projects_table.c.id == project_id).values(**update_values)
                )

        return self.check_budget_status(project_id)