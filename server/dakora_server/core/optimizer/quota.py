"""Quota management for prompt optimization."""

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.engine import Engine
from sqlalchemy.dialects.postgresql import insert as pg_insert

from dakora_server.core.database import (
    get_engine,
    get_connection,
    workspace_quotas_table,
)


def _parse_optimization_quota_tiers() -> dict[str, int]:
    """Parse optimization quota tiers from environment variable or use defaults.

    Format: OPTIMIZATION_QUOTA_TIERS=free=10,starter=50,pro=unlimited

    Returns:
        Dictionary mapping tier names to optimization run limits
    """
    env_tiers = os.getenv("OPTIMIZATION_QUOTA_TIERS")

    if not env_tiers:
        # Default tiers (optimizations per month)
        return {
            "free": 10,  # 10 optimizations/month
            "starter": 50,  # 50 optimizations/month
            "pro": 999999,  # Unlimited (use large number)
        }

    # Parse env variable: tier1=limit1,tier2=limit2,...
    tiers = {}
    for pair in env_tiers.split(","):
        pair = pair.strip()
        if "=" not in pair:
            raise ValueError(f"Invalid tier format: {pair}. Expected 'tier=limit'")

        tier, limit_str = pair.split("=", 1)
        tier = tier.strip()
        limit_str = limit_str.strip()

        # Handle "unlimited" case
        if limit_str.lower() == "unlimited":
            limit = 999999
        else:
            try:
                limit = int(limit_str)
            except ValueError:
                raise ValueError(f"Invalid tier limit for '{tier}': {limit_str}")

            if limit < 0:
                raise ValueError(f"Tier limit must be non-negative: {tier}={limit}")

        tiers[tier] = limit

    return tiers


# Optimization quota tiers (runs per month) - configured via env or defaults
OPTIMIZATION_QUOTA_TIERS = _parse_optimization_quota_tiers()


@dataclass
class OptimizationQuotaUsage:
    """Current optimization quota usage information."""

    workspace_id: str
    tier: str
    optimizations_used: int
    period_start: datetime
    period_end: datetime

    @property
    def optimizations_limit(self) -> int:
        """Calculate optimization limit from tier."""
        return OPTIMIZATION_QUOTA_TIERS.get(self.tier, OPTIMIZATION_QUOTA_TIERS["free"])

    @property
    def optimizations_remaining(self) -> int:
        """Calculate remaining optimization runs."""
        return max(0, self.optimizations_limit - self.optimizations_used)

    @property
    def usage_percentage(self) -> float:
        """Calculate usage as a percentage."""
        if self.optimizations_limit == 0:
            return 0.0
        return (self.optimizations_used / self.optimizations_limit) * 100


class OptimizationQuotaService:
    """Service for managing workspace optimization quota."""

    def __init__(self, engine: Optional[Engine] = None):
        """Initialize optimization quota service.

        Args:
            engine: SQLAlchemy engine (defaults to shared instance)
        """
        self.engine = engine or get_engine()

    def _get_period_dates(self) -> tuple[datetime, datetime]:
        """Get current billing period start/end dates.

        Returns first and last day of current month in UTC.
        """
        now = datetime.now(timezone.utc)
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Get last day of month
        if now.month == 12:
            end = start.replace(year=now.year + 1, month=1)
        else:
            end = start.replace(month=now.month + 1)

        return start, end

    async def check_quota(self, workspace_id: str) -> bool:
        """Check if workspace has available optimization quota.

        Auto-resets quota if new billing period has started.

        Args:
            workspace_id: Workspace UUID

        Returns:
            True if quota available, False if exceeded
        """
        usage = await self.get_usage(workspace_id)
        return usage.optimizations_remaining > 0

    async def consume_quota(self, workspace_id: str) -> None:
        """Decrement quota after successful optimization.

        Auto-creates quota with "free" tier if workspace doesn't have one.

        Args:
            workspace_id: Workspace UUID
        """
        with get_connection(self.engine) as conn:
            # Auto-reset if needed first
            self._auto_reset_if_needed(workspace_id, conn)

            # Update optimization_runs_used_month
            stmt = (
                update(workspace_quotas_table)
                .where(workspace_quotas_table.c.workspace_id == workspace_id)
                .values(
                    optimization_runs_used_month=workspace_quotas_table.c.optimization_runs_used_month + 1,
                    updated_at=datetime.now(timezone.utc),
                )
            )
            result = conn.execute(stmt)

            if result.rowcount == 0:
                # Auto-create quota for existing workspaces (backwards compatibility)
                await self.create_quota(workspace_id, tier="free")
                # Retry the consumption
                result = conn.execute(stmt)

    async def get_usage(self, workspace_id: str) -> OptimizationQuotaUsage:
        """Get current optimization quota usage for workspace.

        Auto-resets quota if new billing period has started.
        Auto-creates quota with "free" tier if workspace doesn't have one.

        Args:
            workspace_id: Workspace UUID

        Returns:
            OptimizationQuotaUsage with current usage stats
        """
        with get_connection(self.engine) as conn:
            # Auto-reset if needed
            self._auto_reset_if_needed(workspace_id, conn)

            stmt = select(workspace_quotas_table).where(
                workspace_quotas_table.c.workspace_id == workspace_id
            )
            result = conn.execute(stmt)
            row = result.fetchone()

            if not row:
                # Auto-create quota for existing workspaces (backwards compatibility)
                return await self.create_quota(workspace_id, tier="free")

            return OptimizationQuotaUsage(
                workspace_id=str(row.workspace_id),
                tier=row.tier,
                optimizations_used=row.optimization_runs_used_month,
                period_start=row.current_period_start,
                period_end=row.current_period_end,
            )

    def _auto_reset_if_needed(self, workspace_id: str, conn) -> None:
        """Reset quota if current period has ended.

        Args:
            workspace_id: Workspace UUID
            conn: SQLAlchemy connection
        """
        period_start, period_end = self._get_period_dates()

        # Check if we need to reset
        stmt = select(workspace_quotas_table.c.current_period_end).where(
            workspace_quotas_table.c.workspace_id == workspace_id
        )
        result = conn.execute(stmt)
        row = result.fetchone()

        if not row:
            return

        current_period_end = row[0]
        now = datetime.now(timezone.utc)

        # If current period has ended, reset quota
        if now >= current_period_end:
            stmt = (
                update(workspace_quotas_table)
                .where(workspace_quotas_table.c.workspace_id == workspace_id)
                .values(
                    optimization_runs_used_month=0,
                    current_period_start=period_start,
                    current_period_end=period_end,
                    updated_at=datetime.now(timezone.utc),
                )
            )
            conn.execute(stmt)
            # Note: get_connection() auto-commits

    async def create_quota(
        self, workspace_id: str, tier: str = "free"
    ) -> OptimizationQuotaUsage:
        """Create quota record for a new workspace.

        Args:
            workspace_id: Workspace UUID
            tier: Quota tier (default: free)

        Returns:
            OptimizationQuotaUsage with initial quota

        Raises:
            ValueError: If tier is invalid
        """
        if tier not in OPTIMIZATION_QUOTA_TIERS:
            raise ValueError(f"Invalid tier: {tier}")

        period_start, period_end = self._get_period_dates()

        with get_connection(self.engine) as conn:
            # Use PostgreSQL-specific INSERT ... ON CONFLICT DO NOTHING
            stmt = pg_insert(workspace_quotas_table).values(
                workspace_id=workspace_id,
                tier=tier,
                tokens_used_month=0,
                optimization_runs_used_month=0,
                current_period_start=period_start,
                current_period_end=period_end,
            )
            stmt = stmt.on_conflict_do_nothing(index_elements=["workspace_id"])
            conn.execute(stmt)

        return await self.get_usage(workspace_id)