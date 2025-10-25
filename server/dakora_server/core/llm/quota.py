"""Quota management for LLM execution."""

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import insert, select, update
from sqlalchemy.engine import Engine
from sqlalchemy.dialects.postgresql import insert as pg_insert

from dakora_server.core.database import (
    get_engine,
    get_connection,
    workspace_quotas_table,
)


# Quota tiers in tokens per month
QUOTA_TIERS = {
    "free": 100_000,  # 100K tokens/month
    "starter": 1_000_000,  # 1M tokens/month
    "pro": 10_000_000,  # 10M tokens/month
}


@dataclass
class QuotaUsage:
    """Current quota usage information."""

    workspace_id: str
    tier: str
    tokens_used: int
    tokens_limit: int
    period_start: datetime
    period_end: datetime

    @property
    def tokens_remaining(self) -> int:
        """Calculate remaining tokens."""
        return max(0, self.tokens_limit - self.tokens_used)

    @property
    def usage_percentage(self) -> float:
        """Calculate usage as a percentage."""
        if self.tokens_limit == 0:
            return 0.0
        return (self.tokens_used / self.tokens_limit) * 100


class QuotaService:
    """Service for managing workspace quota."""

    def __init__(self, engine: Optional[Engine] = None):
        """Initialize quota service.

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
        """Check if workspace has available quota.

        Auto-resets quota if new billing period has started.

        Args:
            workspace_id: Workspace UUID

        Returns:
            True if quota available, False if exceeded
        """
        usage = await self.get_usage(workspace_id)
        return usage.tokens_remaining > 0

    async def consume_quota(self, workspace_id: str, tokens: int) -> None:
        """Decrement quota after successful LLM execution.

        Auto-creates quota with "free" tier if workspace doesn't have one.

        Args:
            workspace_id: Workspace UUID
            tokens: Number of tokens to consume
        """
        with get_connection(self.engine) as conn:
            # Auto-reset if needed first
            self._auto_reset_if_needed(workspace_id, conn)

            # Update tokens_used_month
            stmt = (
                update(workspace_quotas_table)
                .where(workspace_quotas_table.c.workspace_id == workspace_id)
                .values(
                    tokens_used_month=workspace_quotas_table.c.tokens_used_month + tokens,
                    updated_at=datetime.now(timezone.utc),
                )
            )
            result = conn.execute(stmt)

            if result.rowcount == 0:
                # Auto-create quota for existing workspaces (backwards compatibility)
                await self.create_quota(workspace_id, tier="free")
                # Retry the consumption
                result = conn.execute(stmt)

    async def get_usage(self, workspace_id: str) -> QuotaUsage:
        """Get current quota usage for workspace.

        Auto-resets quota if new billing period has started.
        Auto-creates quota with "free" tier if workspace doesn't have one.

        Args:
            workspace_id: Workspace UUID

        Returns:
            QuotaUsage with current usage stats
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

            return QuotaUsage(
                workspace_id=str(row.workspace_id),
                tier=row.tier,
                tokens_used=row.tokens_used_month,
                tokens_limit=row.tokens_limit_month,
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
                    tokens_used_month=0,
                    current_period_start=period_start,
                    current_period_end=period_end,
                    updated_at=datetime.now(timezone.utc),
                )
            )
            conn.execute(stmt)
            # Note: get_connection() auto-commits

    async def create_quota(
        self, workspace_id: str, tier: str = "free"
    ) -> QuotaUsage:
        """Create quota record for a new workspace.

        Args:
            workspace_id: Workspace UUID
            tier: Quota tier (default: free)

        Returns:
            QuotaUsage with initial quota

        Raises:
            ValueError: If tier is invalid
        """
        if tier not in QUOTA_TIERS:
            raise ValueError(f"Invalid tier: {tier}")

        period_start, period_end = self._get_period_dates()
        tokens_limit = QUOTA_TIERS[tier]

        with get_connection(self.engine) as conn:
            # Use PostgreSQL-specific INSERT ... ON CONFLICT DO NOTHING
            stmt = pg_insert(workspace_quotas_table).values(
                workspace_id=workspace_id,
                tier=tier,
                tokens_used_month=0,
                tokens_limit_month=tokens_limit,
                current_period_start=period_start,
                current_period_end=period_end,
            )
            stmt = stmt.on_conflict_do_nothing(index_elements=["workspace_id"])
            conn.execute(stmt)

        return await self.get_usage(workspace_id)