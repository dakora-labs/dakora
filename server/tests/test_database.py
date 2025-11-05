"""Tests for database schema and configuration"""

import os
from dakora_server.core.database import (
    create_db_engine,
    create_test_engine,
    wait_for_db,
    traces_table,
    executions_table,
    template_traces_table,
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


class TestNewSchemaTableDefinitions:
    """Tests for new OTLP-native schema table definitions"""

    def test_traces_table_columns(self):
        """Test traces table has all required columns"""
        columns = {col.name for col in traces_table.columns}

        required_columns = {
            'trace_id', 'project_id', 'provider', 
            'start_time', 'end_time', 'duration_ms',
            'attributes', 'created_at'
        }

        assert columns == required_columns

    def test_traces_table_primary_key(self):
        """Test traces table has trace_id as primary key"""
        pk_columns = [col.name for col in traces_table.primary_key.columns]
        assert pk_columns == ['trace_id']

    def test_executions_table_columns(self):
        """Test executions table has all required columns"""
        columns = {col.name for col in executions_table.columns}

        required_columns = {
            'trace_id', 'span_id', 'parent_span_id', 'project_id',
            'type', 'span_kind', 'agent_id', 'agent_name',
            'provider', 'model', 'start_time', 'end_time', 'latency_ms',
            'tokens_in', 'tokens_out', 
            'input_cost_usd', 'output_cost_usd', 'total_cost_usd',
            'status', 'status_message', 'attributes', 'created_at'
        }

        assert columns == required_columns

    def test_executions_table_primary_key(self):
        """Test executions table has composite primary key (trace_id, span_id)"""
        pk_columns = [col.name for col in executions_table.primary_key.columns]
        assert set(pk_columns) == {'trace_id', 'span_id'}

    def test_executions_table_column_types(self):
        """Test executions table column types are correct"""
        from sqlalchemy import Integer, Text, Numeric, DateTime
        from sqlalchemy.dialects.postgresql import JSONB, UUID

        assert isinstance(executions_table.c.trace_id.type, Text)
        assert isinstance(executions_table.c.span_id.type, Text)
        assert isinstance(executions_table.c.parent_span_id.type, Text)
        assert isinstance(executions_table.c.project_id.type, UUID)
        assert isinstance(executions_table.c.type.type, Text)
        assert isinstance(executions_table.c.span_kind.type, Text)
        assert isinstance(executions_table.c.agent_id.type, Text)
        assert isinstance(executions_table.c.provider.type, Text)
        assert isinstance(executions_table.c.model.type, Text)
        assert isinstance(executions_table.c.start_time.type, DateTime)
        assert isinstance(executions_table.c.end_time.type, DateTime)
        assert isinstance(executions_table.c.tokens_in.type, Integer)
        assert isinstance(executions_table.c.tokens_out.type, Integer)
        assert isinstance(executions_table.c.input_cost_usd.type, Numeric)
        assert isinstance(executions_table.c.output_cost_usd.type, Numeric)
        assert isinstance(executions_table.c.total_cost_usd.type, Numeric)
        assert isinstance(executions_table.c.attributes.type, JSONB)
        assert isinstance(executions_table.c.created_at.type, DateTime)

    def test_template_traces_column_types(self):
        """Test template traces table column types are correct"""
        from sqlalchemy import Integer, String, Text, DateTime
        from sqlalchemy.dialects.postgresql import JSONB, UUID

        assert isinstance(template_traces_table.c.id.type, UUID)
        assert isinstance(template_traces_table.c.trace_id.type, String)
        assert isinstance(template_traces_table.c.span_id.type, Text)  # NEW: links to specific span
        assert isinstance(template_traces_table.c.prompt_id.type, String)
        assert isinstance(template_traces_table.c.version.type, String)
        assert isinstance(template_traces_table.c.inputs_json.type, JSONB)
        assert isinstance(template_traces_table.c.position.type, Integer)
        assert isinstance(template_traces_table.c.role.type, String)
        assert isinstance(template_traces_table.c.source.type, String)
        assert isinstance(template_traces_table.c.message_index.type, Integer)
        assert isinstance(template_traces_table.c.metadata_json.type, JSONB)
        assert isinstance(template_traces_table.c.created_at.type, DateTime)
