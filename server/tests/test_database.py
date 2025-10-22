"""Tests for database connection and management"""

import pytest
import os
from sqlalchemy import text
from dakora_server.core.database import (
    create_db_engine,
    create_test_engine,
    get_connection,
    wait_for_db,
    logs_table,
    get_database_url,
)


@pytest.fixture
def test_db_url():
    """Get test database URL from environment or use default"""
    return os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/dakora"
    )


@pytest.fixture
def test_engine(test_db_url):
    """Create test engine with NullPool for testing"""
    engine = create_test_engine(test_db_url)
    yield engine
    engine.dispose()


class TestDatabaseConnection:
    """Tests for database connection functionality"""

    def test_get_database_url_from_env(self):
        """Test DATABASE_URL is read from environment"""
        test_url = "postgresql://test:test@localhost:5432/test"
        os.environ["DATABASE_URL"] = test_url

        try:
            url = get_database_url()
            assert url == test_url
        finally:
            # Clean up
            if "DATABASE_URL" in os.environ:
                del os.environ["DATABASE_URL"]

    def test_get_database_url_default(self):
        """Test default DATABASE_URL when not set"""
        # Ensure DATABASE_URL is not set
        if "DATABASE_URL" in os.environ:
            old_url = os.environ.pop("DATABASE_URL")
        else:
            old_url = None

        try:
            url = get_database_url()
            assert "postgresql://" in url
            assert "dakora" in url
        finally:
            # Restore original value
            if old_url:
                os.environ["DATABASE_URL"] = old_url

    def test_create_db_engine(self):
        """Test engine creation with default settings"""
        engine = create_db_engine(
            "postgresql://postgres:postgres@localhost:5432/dakora"
        )
        assert engine is not None
        assert engine.pool.size() == 5  # Default pool size
        engine.dispose()

    def test_create_test_engine(self, test_db_url):
        """Test test engine creation with NullPool"""
        engine = create_test_engine(test_db_url)
        assert engine is not None
        # NullPool doesn't maintain connections
        assert hasattr(engine.pool, 'connect')
        engine.dispose()

    @pytest.mark.skipif(
        not os.getenv("DATABASE_URL"),
        reason="DATABASE_URL not set - skipping live database tests"
    )
    def test_get_connection(self, test_engine):
        """Test connection context manager"""
        with get_connection(test_engine) as conn:
            result = conn.execute(text("SELECT 1"))
            assert result.scalar() == 1

    @pytest.mark.skipif(
        not os.getenv("DATABASE_URL"),
        reason="DATABASE_URL not set - skipping live database tests"
    )
    def test_get_connection_rollback_on_error(self, test_engine):
        """Test that connection rolls back on error"""
        with pytest.raises(Exception):
            with get_connection(test_engine) as conn:
                # This should cause an error
                conn.execute(text("SELECT * FROM nonexistent_table"))

    @pytest.mark.skipif(
        not os.getenv("DATABASE_URL"),
        reason="DATABASE_URL not set - skipping live database tests"
    )
    def test_wait_for_db_success(self, test_engine):
        """Test wait_for_db succeeds when database is ready"""
        result = wait_for_db(test_engine, max_retries=5, retry_interval=1)
        assert result is True

    def test_wait_for_db_failure(self):
        """Test wait_for_db fails with invalid connection"""
        bad_engine = create_test_engine(
            "postgresql://invalid:invalid@localhost:9999/invalid"
        )
        result = wait_for_db(bad_engine, max_retries=2, retry_interval=0.1)
        assert result is False
        bad_engine.dispose()


class TestLogsTableSchema:
    """Tests for logs table schema definition"""

    def test_logs_table_columns(self):
        """Test logs table has all required columns"""
        columns = {col.name for col in logs_table.columns}

        required_columns = {
            'id', 'prompt_id', 'version', 'inputs_json', 'output_text',
            'cost', 'latency_ms', 'provider', 'model', 'tokens_in',
            'tokens_out', 'cost_usd', 'created_at'
        }

        assert columns == required_columns

    def test_logs_table_primary_key(self):
        """Test logs table has id as primary key"""
        pk_columns = [col.name for col in logs_table.primary_key.columns]
        assert pk_columns == ['id']

    def test_logs_table_column_types(self):
        """Test logs table column types are correct"""
        from sqlalchemy import Integer, String, Text, Float, DateTime

        assert isinstance(logs_table.c.id.type, Integer)
        assert isinstance(logs_table.c.prompt_id.type, String)
        assert isinstance(logs_table.c.version.type, String)
        assert isinstance(logs_table.c.inputs_json.type, Text)
        assert isinstance(logs_table.c.output_text.type, Text)
        assert isinstance(logs_table.c.cost.type, Float)
        assert isinstance(logs_table.c.latency_ms.type, Integer)
        assert isinstance(logs_table.c.provider.type, String)
        assert isinstance(logs_table.c.model.type, String)
        assert isinstance(logs_table.c.tokens_in.type, Integer)
        assert isinstance(logs_table.c.tokens_out.type, Integer)
        assert isinstance(logs_table.c.cost_usd.type, Float)
        assert isinstance(logs_table.c.created_at.type, DateTime)