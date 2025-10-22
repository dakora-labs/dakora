"""Database connection and schema management using SQLAlchemy Core"""

from __future__ import annotations
import os
import time
import logging
from typing import Optional, Any
from contextlib import contextmanager

from sqlalchemy import (
    create_engine,
    MetaData,
    Table,
    Column,
    Integer,
    String,
    Text,
    Float,
    DateTime,
    ForeignKey,
    text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool

logger = logging.getLogger(__name__)


metadata = MetaData()

# Logs table definition (SQLAlchemy Core)
logs_table = Table(
    "logs",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("prompt_id", String(255)),
    Column("version", String(50)),
    Column("inputs_json", Text),
    Column("output_text", Text),
    Column("cost", Float),  # type: ignore[misc]
    Column("latency_ms", Integer),
    Column("provider", String(50)),
    Column("model", String(100)),
    Column("tokens_in", Integer),
    Column("tokens_out", Integer),
    Column("cost_usd", Float),  # type: ignore[misc]
    Column("created_at", DateTime, server_default=text("CURRENT_TIMESTAMP")),
)

# Users table definition (SQLAlchemy Core)
users_table = Table(
    "users",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("clerk_user_id", String(255), nullable=False, unique=True, index=True),
    Column("email", String(255), nullable=False),
    Column("name", String(255), nullable=True),
    Column("created_at", DateTime, server_default=text("NOW()"), nullable=False),
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
    Column("created_at", DateTime, server_default=text("NOW()"), nullable=False),
)

# Workspace members table definition (SQLAlchemy Core)
workspace_members_table = Table(
    "workspace_members",
    metadata,
    Column("workspace_id", UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("role", String(20), nullable=False),
    Column("joined_at", DateTime, server_default=text("NOW()"), nullable=False),
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
    Column("created_at", DateTime, server_default=text("NOW()"), nullable=False),
    Column("updated_at", DateTime, server_default=text("NOW()"), nullable=False),
)

# Prompts table definition (SQLAlchemy Core)
prompts_table = Table(
    "prompts",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
    Column("project_id", UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("prompt_id", String(255), nullable=False),
    Column("version", String(50), nullable=False),
    Column("description", Text, nullable=True),
    Column("storage_path", Text, nullable=False),
    Column("last_updated_at", DateTime, server_default=text("NOW()"), nullable=False, index=True),
    Column("created_at", DateTime, server_default=text("NOW()"), nullable=False),
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
    Column("created_at", DateTime, server_default=text("NOW()"), nullable=False),
    Column("updated_at", DateTime, server_default=text("NOW()"), nullable=False),
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
