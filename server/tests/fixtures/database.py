"""Database fixtures for testing.

Provides database connections and session management for tests.
"""

import pytest
from typing import Generator
from contextlib import contextmanager
from sqlalchemy.engine import Engine, Connection

from dakora_server.core.database import create_db_engine, get_connection


@pytest.fixture(scope="session")
def db_engine() -> Generator[Engine, None, None]:
    """Create a database engine for the entire test session.

    Session-scoped to reuse connection pool across all tests.
    """
    engine = create_db_engine()
    yield engine
    engine.dispose()


@pytest.fixture
def db_connection(db_engine: Engine) -> Generator[Connection, None, None]:
    """Provide a database connection for a test.

    Function-scoped so each test gets a fresh connection.
    Automatically commits on success, rolls back on failure.

    Example:
        def test_create_user(db_connection):
            # Use db_connection to execute queries
            result = db_connection.execute(...)
    """
    with get_connection(db_engine) as conn:
        yield conn


@pytest.fixture
@contextmanager
def db_session_scope(db_connection: Connection):
    """Provide a context manager for nested database sessions.

    Useful when you need to create test data that should be committed
    before running the actual test.

    Example:
        def test_with_committed_data(db_session_scope):
            # Setup data in a committed transaction
            with db_session_scope() as conn:
                create_test_user(conn)
                # Data is committed here

            # Now run test with committed data
            result = api_call_that_reads_db()
    """
    try:
        yield db_connection
        db_connection.commit()
    except Exception:
        db_connection.rollback()
        raise
