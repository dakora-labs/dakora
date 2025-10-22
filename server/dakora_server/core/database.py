"""Database connection and schema management using SQLAlchemy Core"""

from __future__ import annotations
import os
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
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool


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
    Context manager for database connections.

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
    import time

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
