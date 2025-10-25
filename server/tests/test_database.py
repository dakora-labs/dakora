"""Tests for database schema and configuration"""

import os
from dakora_server.core.database import (
    create_db_engine,
    create_test_engine,
    wait_for_db,
    traces_table,
    get_database_url,
)


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

    def test_create_test_engine(self):
        """Test test engine creation with NullPool"""
        engine = create_test_engine(
            "postgresql://postgres:postgres@localhost:5432/dakora"
        )
        assert engine is not None
        # NullPool doesn't maintain connections
        assert hasattr(engine.pool, 'connect')
        engine.dispose()

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

    def test_traces_table_columns(self):
        """Test logs table has all required columns for trace-based logging"""
        columns = {col.name for col in traces_table.columns}

        required_columns = {
            # Primary key and trace identifiers
            'id', 'trace_id', 'session_id', 'parent_trace_id', 'agent_id',
            # Project context
            'project_id',
            # Execution data (trace-based)
            'conversation_history', 'metadata',
            # LLM details
            'provider', 'model',
            # Metrics
            'tokens_in', 'tokens_out', 'latency_ms', 'cost_usd',
            'created_at',
            # Legacy columns (for backward compatibility)
            'prompt_id', 'version', 'inputs_json', 'output_text', 'cost'
        }

        assert columns == required_columns

    def test_traces_table_primary_key(self):
        """Test logs table has id as primary key"""
        pk_columns = [col.name for col in traces_table.primary_key.columns]
        assert pk_columns == ['id']

    def test_traces_table_column_types(self):
        """Test logs table column types are correct"""
        from sqlalchemy import Integer, String, Text, Float, DateTime
        from sqlalchemy.dialects.postgresql import JSONB, UUID

        # Primary key and trace identifiers
        assert isinstance(traces_table.c.id.type, Integer)
        assert isinstance(traces_table.c.trace_id.type, String)
        assert isinstance(traces_table.c.session_id.type, String)
        assert isinstance(traces_table.c.parent_trace_id.type, String)
        assert isinstance(traces_table.c.agent_id.type, String)
        
        # Project context
        assert isinstance(traces_table.c.project_id.type, UUID)
        
        # Execution data (trace-based)
        assert isinstance(traces_table.c.conversation_history.type, JSONB)
        assert isinstance(traces_table.c.metadata.type, JSONB)
        
        # LLM details
        assert isinstance(traces_table.c.provider.type, String)
        assert isinstance(traces_table.c.model.type, String)
        
        # Metrics
        assert isinstance(traces_table.c.tokens_in.type, Integer)
        assert isinstance(traces_table.c.tokens_out.type, Integer)
        assert isinstance(traces_table.c.latency_ms.type, Integer)
        assert isinstance(traces_table.c.cost_usd.type, Float)
        assert isinstance(traces_table.c.created_at.type, DateTime)
        
        # Legacy columns
        assert isinstance(traces_table.c.prompt_id.type, String)
        assert isinstance(traces_table.c.version.type, String)
        assert isinstance(traces_table.c.inputs_json.type, Text)
        assert isinstance(traces_table.c.output_text.type, Text)
        assert isinstance(traces_table.c.cost.type, Float)
