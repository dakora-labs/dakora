"""Database connection and schema management using SQLAlchemy Core"""

from __future__ import annotations

import logging
import os
import time
from contextlib import contextmanager
from typing import Any, Optional

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    Text,
    create_engine,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool

logger = logging.getLogger(__name__)


metadata = MetaData()

# Execution traces table - trace-based observability
# Tracks all LLM executions with optional template linkage
traces_table = Table(
    "execution_traces",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    # Trace identifiers
    Column("trace_id", String(255), unique=True, nullable=False, index=True),
    Column("session_id", String(255), nullable=True, index=True),
    Column("parent_trace_id", String(255), nullable=True, index=True),  # For nested calls (future)
    Column("agent_id", String(255), nullable=True, index=True),
    Column("source", String(50), nullable=True, index=True),
    # Project context
    Column(
        "project_id",
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    ),
    # Execution data
    Column("conversation_history", JSONB, nullable=True),  # Full conversation context
    Column("metadata", JSONB, nullable=True),  # Additional context (user_id, tags, etc.)
    # LLM details
    Column("provider", String(50), nullable=True),
    Column("model", String(100), nullable=True),
    # Metrics
    Column("tokens_in", Integer, nullable=True),
    Column("tokens_out", Integer, nullable=True),
    Column("latency_ms", Integer, nullable=True),
    Column("cost_usd", Float, nullable=True),  # type: ignore[misc]
    Column("created_at", DateTime(timezone=True), server_default=text("(NOW() AT TIME ZONE 'UTC')")),
    # Legacy columns (kept for backward compatibility)
    Column("prompt_id", String(255), nullable=True),
    Column("version", String(50), nullable=True),
    Column("inputs_json", Text, nullable=True),
    Column("output_text", Text, nullable=True),
    Column("cost", Float, nullable=True),  # type: ignore[misc]
)

# Template traces table - links templates to execution traces
# Supports multiple templates per execution (multi-turn conversations)
template_traces_table = Table(
    "template_traces",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column(
        "trace_id",
        String(255),
        ForeignKey("execution_traces.trace_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
    Column("prompt_id", String(255), nullable=False, index=True),
    Column("version", String(50), nullable=False),
    Column("inputs_json", JSONB, nullable=True),
    Column("position", Integer, nullable=True),  # Position in conversation (0=first, 1=second, etc.)
    Column("role", String(50), nullable=True),
    Column("source", String(50), nullable=True),
    Column("message_index", Integer, nullable=True),
    Column("metadata_json", JSONB, nullable=True),
    Column("created_at", DateTime, server_default=text("NOW()"), nullable=False),
)

# Users table definition (SQLAlchemy Core)
users_table = Table(
    "users",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("clerk_user_id", String(255), nullable=False, unique=True, index=True),
    Column("email", String(255), nullable=False),
    Column("name", String(255), nullable=True),
    Column("created_at", DateTime(timezone=True), server_default=text("(NOW() AT TIME ZONE 'UTC')"), nullable=False),
)

# Workspaces table definition (SQLAlchemy Core)
workspaces_table = Table(
    "workspaces",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("slug", String(63), nullable=False, unique=True, index=True),
    Column("name", String(255), nullable=False),
    Column("type", String(20), nullable=False),
    Column("owner_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("created_at", DateTime(timezone=True), server_default=text("(NOW() AT TIME ZONE 'UTC')"), nullable=False),
)

# Workspace members table definition (SQLAlchemy Core)
workspace_members_table = Table(
    "workspace_members",
    metadata,
    Column("workspace_id", UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("role", String(20), nullable=False),
    Column("joined_at", DateTime(timezone=True), server_default=text("(NOW() AT TIME ZONE 'UTC')"), nullable=False),
)

# Projects table definition (SQLAlchemy Core)
projects_table = Table(
    "projects",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("workspace_id", UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("slug", String(63), nullable=False),
    Column("name", String(255), nullable=False),
    Column("description", Text, nullable=True),
    Column("created_at", DateTime(timezone=True), server_default=text("(NOW() AT TIME ZONE 'UTC')"), nullable=False),
    Column("updated_at", DateTime(timezone=True), server_default=text("(NOW() AT TIME ZONE 'UTC')"), nullable=False),
    Column("budget_monthly_usd", Numeric(10, 2), nullable=True),
    Column("alert_threshold_pct", Integer, server_default=text("80"), nullable=False),
    Column("budget_enforcement_mode", String(20), server_default=text("'strict'"), nullable=False),
)

# Prompts table definition (SQLAlchemy Core)
prompts_table = Table(
    "prompts",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("project_id", UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("prompt_id", String(255), nullable=False),
    Column("version", String(50), nullable=False),
    Column("version_number", Integer, server_default="1", nullable=False),
    Column("content_hash", String(64), nullable=True),
    Column("description", Text, nullable=True),
    Column("storage_path", Text, nullable=False),
    Column("last_updated_at", DateTime(timezone=True), server_default=text("(NOW() AT TIME ZONE 'UTC')"), nullable=False, index=True),
    Column("created_at", DateTime(timezone=True), server_default=text("(NOW() AT TIME ZONE 'UTC')"), nullable=False),
    Column("metadata", JSONB, nullable=True),
)

# Prompt versions table definition (SQLAlchemy Core)
prompt_versions_table = Table(
    "prompt_versions",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("prompt_id", UUID(as_uuid=True), ForeignKey("prompts.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("version_number", Integer, nullable=False),
    Column("content_hash", String(64), nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=text("(NOW() AT TIME ZONE 'UTC')"), nullable=False, index=True),
    Column("created_by", UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    Column("storage_path", Text, nullable=False),
    Column("metadata", JSONB, nullable=True),
)

# Prompt parts table definition (SQLAlchemy Core)
prompt_parts_table = Table(
    "prompt_parts",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("project_id", UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("part_id", String(255), nullable=False),
    Column("category", String(63), nullable=False),
    Column("name", String(255), nullable=False),
    Column("description", Text, nullable=True),
    Column("content", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=text("(NOW() AT TIME ZONE 'UTC')"), nullable=False),
    Column("updated_at", DateTime(timezone=True), server_default=text("(NOW() AT TIME ZONE 'UTC')"), nullable=False),
)

# API keys table definition (SQLAlchemy Core)
api_keys_table = Table(
    "api_keys",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("project_id", UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("name", String(255), nullable=True),
    Column("key_prefix", String(8), nullable=False),
    Column("key_suffix", String(4), nullable=False),
    Column("key_hash", String(255), nullable=False, index=True),
    Column("created_at", DateTime(timezone=True), server_default=text("(NOW() AT TIME ZONE 'UTC')"), nullable=False),
    Column("last_used_at", DateTime(timezone=True), nullable=True),
    Column("expires_at", DateTime(timezone=True), nullable=True, index=True),
    Column("revoked_at", DateTime(timezone=True), nullable=True),
)

# Workspace quotas table definition (SQLAlchemy Core)
workspace_quotas_table = Table(
    "workspace_quotas",
    metadata,
    Column("workspace_id", UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), primary_key=True),
    Column("tier", String(50), nullable=False, server_default="free"),
    Column("tokens_used_month", Integer, nullable=False, server_default="0"),
    Column("optimization_runs_used_month", Integer, nullable=False, server_default="0"),
    Column("current_period_start", DateTime(timezone=True), nullable=False),
    Column("current_period_end", DateTime(timezone=True), nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=text("(NOW() AT TIME ZONE 'UTC')"), nullable=False),
    Column("updated_at", DateTime(timezone=True), server_default=text("(NOW() AT TIME ZONE 'UTC')"), nullable=False),
)

# Prompt executions table definition (SQLAlchemy Core)
prompt_executions_table = Table(
    "prompt_executions",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("project_id", UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("prompt_id", String(255), nullable=False),
    Column("version", String(50), nullable=False),
    Column("trace_id", String(255), nullable=True, index=True),
    # Execution details
    Column("inputs_json", JSONB, nullable=False),
    Column("model", String(100), nullable=False),
    Column("provider", String(50), nullable=False),
    # Results
    Column("output_text", Text, nullable=True),
    Column("error_message", Text, nullable=True),
    Column("status", String(20), nullable=False),
    # Metrics
    Column("tokens_input", Integer, nullable=True),
    Column("tokens_output", Integer, nullable=True),
    Column("tokens_total", Integer, nullable=True),
    Column("cost_usd", Numeric(10, 6), nullable=True),
    Column("latency_ms", Integer, nullable=True),
    # Metadata
    Column("user_id", String(255), nullable=False),
    Column("workspace_id", UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("created_at", DateTime(timezone=True), server_default=text("(NOW() AT TIME ZONE 'UTC')"), nullable=False, index=True),
)

# Optimization runs table definition (SQLAlchemy Core)
optimization_runs_table = Table(
    "optimization_runs",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("project_id", UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("prompt_id", String(255), nullable=False, index=True),
    Column("version", String(50), nullable=False),
    Column("original_template", Text, nullable=False),
    Column("optimized_template", Text, nullable=False),
    Column("insights", JSONB, nullable=True),
    Column("token_reduction_pct", Float, nullable=True),  # type: ignore[misc]
    Column("applied", Integer, server_default="0", nullable=False),  # 0=not applied, 1=applied
    Column("user_id", String(255), nullable=False),
    Column("workspace_id", UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("created_at", DateTime(timezone=True), server_default=text("(NOW() AT TIME ZONE 'UTC')"), nullable=False, index=True),
)

# OpenTelemetry spans table - raw OTLP storage
# Stores complete OTLP spans for debugging and trace visualization
otel_spans_table = Table(
    "otel_spans",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    # OTLP identifiers
    Column("trace_id", String(32), nullable=False, index=True),
    Column("span_id", String(16), nullable=False, unique=True, index=True),
    Column("parent_span_id", String(16), nullable=True, index=True),
    # Project context
    Column("project_id", UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True),
    # Span metadata
    Column("span_name", String(255), nullable=False),
    Column("span_kind", String(50), nullable=True),
    # OTLP data (raw storage)
    Column("attributes", JSONB, nullable=True),
    Column("events", JSONB, nullable=True),
    # Timing
    Column("start_time_ns", Integer, nullable=False),
    Column("end_time_ns", Integer, nullable=False),
    Column("duration_ns", Integer, nullable=False),
    # Status
    Column("status_code", String(20), nullable=True),
    Column("status_message", String(255), nullable=True),
    # Timestamps
    Column("created_at", DateTime(timezone=True), server_default=text("(NOW() AT TIME ZONE 'UTC')"), nullable=False),
)


def get_database_url() -> str:
    """Get database URL from environment or use default for local dev"""
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        # Default for local development
        database_url = "postgresql://postgres:postgres@localhost:5432/dakora"

    return database_url


def create_db_engine(database_url: Optional[str] = None, **kwargs: Any) -> Engine:
    """
    Create SQLAlchemy engine with connection pooling.

    Args:
        database_url: PostgreSQL connection string (defaults to DATABASE_URL env var)
        **kwargs: Additional engine options

    Returns:
        SQLAlchemy Engine instance
    """
    url = database_url or get_database_url()

    # Default engine options for production reliability
    engine_options: dict[str, Any] = {
        "pool_pre_ping": True,  # Verify connections before using
        "pool_recycle": 3600,  # Recycle connections after 1 hour
        "pool_size": 5,  # Connection pool size
        "max_overflow": 10,  # Max overflow connections
        "echo": False,  # Set to True for SQL debugging
    }

    # Allow override of defaults
    engine_options.update(kwargs)

    return create_engine(url, **engine_options)


# Global engine instance - created once and reused across all requests
_global_engine: Optional[Engine] = None


def get_engine() -> Engine:
    """
    Get or create the global database engine instance.
    
    This function ensures we reuse the same connection pool across all requests
    instead of creating a new engine (and pool) for each request.
    
    Returns:
        Global SQLAlchemy Engine instance
    """
    global _global_engine
    
    if _global_engine is None:
        _global_engine = create_db_engine()
    
    return _global_engine


def create_test_engine(database_url: str) -> Engine:
    """
    Create engine for testing with NullPool (no connection pooling).

    Args:
        database_url: PostgreSQL connection string

    Returns:
        SQLAlchemy Engine instance with NullPool
    """
    return create_engine(
        database_url,
        poolclass=NullPool,
        echo=False,
    )


@contextmanager
def get_connection(engine: Engine):
    """
    Context manager for database connections with timing logging.

    Usage:
        with get_connection(engine) as conn:
            result = conn.execute(...)
    """
    conn = engine.connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def wait_for_db(engine: Engine, max_retries: int = 30, retry_interval: int = 1) -> bool:
    """
    Wait for database to be ready (used in Docker entrypoint).

    Args:
        engine: SQLAlchemy Engine instance
        max_retries: Maximum number of connection attempts
        retry_interval: Seconds between retries

    Returns:
        True if database is ready, False otherwise
    """
    for attempt in range(max_retries):
        try:
            with get_connection(engine) as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            if attempt < max_retries - 1:
                print(
                    f"Database not ready (attempt {attempt + 1}/{max_retries}), retrying in {retry_interval}s..."
                )
                time.sleep(retry_interval)
            else:
                print(
                    f"Failed to connect to database after {max_retries} attempts: {e}"
                )
                return False

    return False
