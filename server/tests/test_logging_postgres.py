"""Tests for Logger with PostgreSQL backend"""

import pytest
import os
from datetime import datetime
from sqlalchemy import select, func
from dakora_server.core.logging import Logger
from dakora_server.core.database import (
    create_test_engine,
    get_connection,
    logs_table,
    metadata,
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
    """Create test engine and setup tables"""
    engine = create_test_engine(test_db_url)

    # Always ensure tables exist before each test
    # In production, Alembic handles this
    metadata.create_all(engine)

    # Clear any existing data for clean slate
    try:
        with get_connection(engine) as conn:
            conn.execute(logs_table.delete())
            conn.commit()
    except Exception:
        # Ignore if table doesn't exist yet
        pass

    yield engine

    # Cleanup: just delete rows, don't drop tables
    try:
        with get_connection(engine) as conn:
            conn.execute(logs_table.delete())
            conn.commit()
    except Exception:
        # Ignore cleanup errors
        pass

    engine.dispose()


@pytest.fixture
def logger(test_engine):
    """Create Logger instance for testing"""
    logger = Logger(engine=test_engine)
    yield logger
    logger.close()


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set - skipping live database tests"
)
class TestLogger:
    """Tests for Logger class with PostgreSQL"""

    def test_logger_init(self, logger):
        """Test Logger initializes with engine"""
        assert logger.engine is not None

    def test_logger_init_without_engine(self):
        """Test Logger creates engine when none provided"""
        # Uses DATABASE_URL from environment
        logger = Logger()
        assert logger.engine is not None
        logger.close()

    def test_write_basic_log(self, logger, test_engine):
        """Test writing basic execution log"""
        logger.write(
            prompt_id="test-template",
            version="1.0.0",
            inputs={"name": "Alice"},
            output="Hello Alice!",
        )

        # Verify log was written
        with get_connection(test_engine) as conn:
            stmt = select(logs_table).where(logs_table.c.prompt_id == "test-template")
            result = conn.execute(stmt).fetchone()

            assert result is not None
            assert result.prompt_id == "test-template"
            assert result.version == "1.0.0"
            assert '{"name": "Alice"}' in result.inputs_json or '{"name":"Alice"}' in result.inputs_json
            assert result.output_text == "Hello Alice!"

    def test_write_log_with_llm_metrics(self, logger, test_engine):
        """Test writing log with LLM execution metrics"""
        logger.write(
            prompt_id="llm-template",
            version="2.0.0",
            inputs={"query": "What is AI?"},
            output="AI is artificial intelligence...",
            latency_ms=1234,
            provider="openai",
            model="gpt-4",
            tokens_in=50,
            tokens_out=100,
            cost_usd=0.0015,
        )

        # Verify all fields were written
        with get_connection(test_engine) as conn:
            stmt = select(logs_table).where(logs_table.c.prompt_id == "llm-template")
            result = conn.execute(stmt).fetchone()

            assert result is not None
            assert result.latency_ms == 1234
            assert result.provider == "openai"
            assert result.model == "gpt-4"
            assert result.tokens_in == 50
            assert result.tokens_out == 100
            assert result.cost_usd == 0.0015

    def test_write_log_with_null_values(self, logger, test_engine):
        """Test writing log with optional null values"""
        logger.write(
            prompt_id="minimal-template",
            version="1.0.0",
            inputs={},
            output="Output",
            cost=None,
            latency_ms=None,
            provider=None,
            model=None,
            tokens_in=None,
            tokens_out=None,
            cost_usd=None,
        )

        # Verify log was written with nulls
        with get_connection(test_engine) as conn:
            stmt = select(logs_table).where(logs_table.c.prompt_id == "minimal-template")
            result = conn.execute(stmt).fetchone()

            assert result is not None
            assert result.cost is None
            assert result.latency_ms is None
            assert result.provider is None
            assert result.model is None

    def test_write_multiple_logs(self, logger, test_engine):
        """Test writing multiple logs"""
        for i in range(5):
            logger.write(
                prompt_id=f"template-{i}",
                version="1.0.0",
                inputs={"index": i},
                output=f"Output {i}",
            )

        # Verify all logs were written
        with get_connection(test_engine) as conn:
            stmt = select(func.count()).select_from(logs_table)
            count = conn.execute(stmt).scalar()
            assert count >= 5  # At least 5 (might have more from other tests)

    def test_write_log_with_complex_inputs(self, logger, test_engine):
        """Test writing log with complex JSON inputs"""
        complex_inputs = {
            "name": "Alice",
            "settings": {
                "theme": "dark",
                "notifications": True,
            },
            "tags": ["important", "urgent"],
        }

        logger.write(
            prompt_id="complex-template",
            version="1.0.0",
            inputs=complex_inputs,
            output="Processed",
        )

        # Verify complex JSON was stored correctly
        with get_connection(test_engine) as conn:
            stmt = select(logs_table).where(logs_table.c.prompt_id == "complex-template")
            result = conn.execute(stmt).fetchone()

            assert result is not None
            # JSON should contain nested structures
            assert "settings" in result.inputs_json
            assert "tags" in result.inputs_json

    def test_created_at_timestamp(self, logger, test_engine):
        """Test that created_at timestamp is set automatically"""
        logger.write(
            prompt_id="timestamp-test",
            version="1.0.0",
            inputs={},
            output="Test",
        )

        with get_connection(test_engine) as conn:
            stmt = select(logs_table).where(logs_table.c.prompt_id == "timestamp-test")
            result = conn.execute(stmt).fetchone()

            assert result is not None
            assert result.created_at is not None
            assert isinstance(result.created_at, datetime)

    def test_logger_close(self, test_engine):
        """Test Logger.close() disposes engine"""
        logger = Logger(engine=test_engine)
        logger.close()
        # Engine should be disposed (pool closed)
        # Note: We can't easily test this without checking internal state
        # Just verify close() doesn't raise an error


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set - skipping live database tests"
)
class TestLoggerIntegration:
    """Integration tests for Logger"""

    def test_concurrent_writes(self, logger, test_engine):
        """Test that multiple writes work correctly"""
        import threading

        def write_logs(prefix, count):
            for i in range(count):
                logger.write(
                    prompt_id=f"{prefix}-{i}",
                    version="1.0.0",
                    inputs={"thread": prefix, "index": i},
                    output=f"Output {prefix}-{i}",
                )

        # Create multiple threads writing logs
        threads = []
        for i in range(3):
            t = threading.Thread(target=write_logs, args=(f"thread-{i}", 5))
            threads.append(t)
            t.start()

        # Wait for all threads to complete
        for t in threads:
            t.join()

        # Verify all logs were written
        with get_connection(test_engine) as conn:
            stmt = select(func.count()).select_from(logs_table).where(
                logs_table.c.prompt_id.like("thread-%")
            )
            count = conn.execute(stmt).scalar()
            assert count >= 15  # 3 threads * 5 logs each