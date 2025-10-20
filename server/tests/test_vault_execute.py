import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import yaml
import pytest
import gc
import time
import os

from dakora_server.core.vault import Vault
from dakora_server.core.llm.models import ExecutionResult
from dakora_server.core.exceptions import ValidationError, APIKeyError, RateLimitError, ModelNotFoundError, LLMError
from dakora_server.core.database import create_test_engine, metadata
from dakora_server.core.logging import Logger


@pytest.fixture
def temp_vault_with_logging():
    with tempfile.TemporaryDirectory() as tmpdir:
        prompts_dir = Path(tmpdir) / "prompts"
        prompts_dir.mkdir()

        test_template = {
            "id": "test-template",
            "version": "1.0.0",
            "description": "Test template for execution",
            "template": "Summarize this text: {{ text }}",
            "inputs": {
                "text": {
                    "type": "string",
                    "required": True
                }
            }
        }

        template_path = prompts_dir / "test-template.yaml"
        template_path.write_text(yaml.safe_dump(test_template))

        config = {
            "registry": "local",
            "prompt_dir": str(prompts_dir),
            "logging": {
                "enabled": True,
                "backend": "sqlite",
                "db_path": str(Path(tmpdir) / "dakora.db")
            }
        }

        config_path = Path(tmpdir) / "dakora.yaml"
        config_path.write_text(yaml.safe_dump(config))

        vault = Vault(str(config_path))
        try:
            yield vault, tmpdir
        finally:
            # Close vault to release database file locks on Windows
            vault.close()
            # Force garbage collection to release any remaining references
            gc.collect()
            # Small delay to allow Windows to release file locks
            time.sleep(0.1)


@pytest.fixture
def temp_vault_no_logging():
    with tempfile.TemporaryDirectory() as tmpdir:
        prompts_dir = Path(tmpdir) / "prompts"
        prompts_dir.mkdir()

        test_template = {
            "id": "test-template",
            "version": "1.0.0",
            "description": "Test template for execution",
            "template": "Summarize this text: {{ text }}",
            "inputs": {
                "text": {
                    "type": "string",
                    "required": True
                }
            }
        }

        template_path = prompts_dir / "test-template.yaml"
        template_path.write_text(yaml.safe_dump(test_template))

        vault = Vault(prompt_dir=str(prompts_dir))
        yield vault


@pytest.fixture
def mock_execution_result():
    return ExecutionResult(
        output="This is a summary of the text.",
        provider="openai",
        model="gpt-4",
        tokens_in=100,
        tokens_out=50,
        cost_usd=0.05,
        latency_ms=1200
    )


class TestTemplateHandleExecute:
    def test_execute_basic_success(self, temp_vault_no_logging, mock_execution_result):
        vault = temp_vault_no_logging
        template = vault.get("test-template")

        with patch.object(template, '_llm_client', None):
            with patch('dakora_server.core.vault.LLMClient') as mock_client_class:
                mock_client = Mock()
                mock_client.execute.return_value = mock_execution_result
                mock_client_class.return_value = mock_client

                result = template.execute(model="gpt-4", text="Sample text to summarize")

                assert result == mock_execution_result
                assert result.output == "This is a summary of the text."
                assert result.provider == "openai"
                assert result.model == "gpt-4"
                assert result.tokens_in == 100
                assert result.tokens_out == 50
                assert result.cost_usd == 0.05
                assert result.latency_ms == 1200

                mock_client.execute.assert_called_once()
                call_args = mock_client.execute.call_args
                assert call_args[0][0] == "Summarize this text: Sample text to summarize"
                assert call_args[0][1] == "gpt-4"

    def test_execute_with_llm_params(self, temp_vault_no_logging, mock_execution_result):
        vault = temp_vault_no_logging
        template = vault.get("test-template")

        with patch.object(template, '_llm_client', None):
            with patch('dakora_server.core.vault.LLMClient') as mock_client_class:
                mock_client = Mock()
                mock_client.execute.return_value = mock_execution_result
                mock_client_class.return_value = mock_client

                result = template.execute(
                    model="gpt-4",
                    text="Sample text",
                    temperature=0.7,
                    max_tokens=100,
                    top_p=0.9
                )

                assert result == mock_execution_result

                call_args = mock_client.execute.call_args
                assert call_args[1]["temperature"] == 0.7
                assert call_args[1]["max_tokens"] == 100
                assert call_args[1]["top_p"] == 0.9

    def test_execute_with_logging(self, temp_vault_with_logging, mock_execution_result):
        vault, tmpdir = temp_vault_with_logging
        template = vault.get("test-template")

        # Mock logger to avoid database dependency in unit tests
        mock_logger = Mock()

        with patch.object(template, '_llm_client', None):
            with patch.object(vault, 'logger', mock_logger):
                with patch('dakora_server.core.vault.LLMClient') as mock_client_class:
                    mock_client = Mock()
                    mock_client.execute.return_value = mock_execution_result
                    mock_client_class.return_value = mock_client

                    result = template.execute(model="gpt-4", text="Sample text")

                    assert result == mock_execution_result

                    # Verify logger was called with correct parameters
                    mock_logger.write.assert_called_once()
                    call_args = mock_logger.write.call_args
                    assert call_args[1]["prompt_id"] == "test-template"
                    assert call_args[1]["version"] == "1.0.0"
                    assert call_args[1]["provider"] == "openai"
                    assert call_args[1]["model"] == "gpt-4"
                    assert call_args[1]["tokens_in"] == 100
                    assert call_args[1]["tokens_out"] == 50
                    assert call_args[1]["cost_usd"] == 0.05

    def test_execute_validation_error(self, temp_vault_no_logging):
        vault = temp_vault_no_logging
        template = vault.get("test-template")

        with pytest.raises(ValidationError):
            template.execute(model="gpt-4")

    def test_execute_api_key_error(self, temp_vault_no_logging):
        vault = temp_vault_no_logging
        template = vault.get("test-template")

        with patch.object(template, '_llm_client', None):
            with patch('dakora_server.core.vault.LLMClient') as mock_client_class:
                mock_client = Mock()
                mock_client.execute.side_effect = APIKeyError("Invalid API key")
                mock_client_class.return_value = mock_client

                with pytest.raises(APIKeyError) as exc_info:
                    template.execute(model="gpt-4", text="Sample text")

                assert "Invalid API key" in str(exc_info.value)

    def test_execute_rate_limit_error(self, temp_vault_no_logging):
        vault = temp_vault_no_logging
        template = vault.get("test-template")

        with patch.object(template, '_llm_client', None):
            with patch('dakora_server.core.vault.LLMClient') as mock_client_class:
                mock_client = Mock()
                mock_client.execute.side_effect = RateLimitError("Rate limit exceeded")
                mock_client_class.return_value = mock_client

                with pytest.raises(RateLimitError) as exc_info:
                    template.execute(model="gpt-4", text="Sample text")

                assert "Rate limit exceeded" in str(exc_info.value)

    def test_execute_model_not_found_error(self, temp_vault_no_logging):
        vault = temp_vault_no_logging
        template = vault.get("test-template")

        with patch.object(template, '_llm_client', None):
            with patch('dakora_server.core.vault.LLMClient') as mock_client_class:
                mock_client = Mock()
                mock_client.execute.side_effect = ModelNotFoundError("Model not found")
                mock_client_class.return_value = mock_client

                with pytest.raises(ModelNotFoundError) as exc_info:
                    template.execute(model="invalid-model", text="Sample text")

                assert "Model not found" in str(exc_info.value)

    def test_execute_llm_error(self, temp_vault_no_logging):
        vault = temp_vault_no_logging
        template = vault.get("test-template")

        with patch.object(template, '_llm_client', None):
            with patch('dakora_server.core.vault.LLMClient') as mock_client_class:
                mock_client = Mock()
                mock_client.execute.side_effect = LLMError("Unexpected error")
                mock_client_class.return_value = mock_client

                with pytest.raises(LLMError) as exc_info:
                    template.execute(model="gpt-4", text="Sample text")

                assert "Unexpected error" in str(exc_info.value)

    def test_execute_client_reuse(self, temp_vault_no_logging, mock_execution_result):
        vault = temp_vault_no_logging
        template = vault.get("test-template")

        with patch.object(template, '_llm_client', None):
            with patch('dakora_server.core.vault.LLMClient') as mock_client_class:
                mock_client = Mock()
                mock_client.execute.return_value = mock_execution_result
                mock_client_class.return_value = mock_client

                template.execute(model="gpt-4", text="First execution")
                template.execute(model="gpt-4", text="Second execution")

                assert mock_client_class.call_count == 1
                assert mock_client.execute.call_count == 2

    def test_execute_with_complex_template(self, temp_vault_no_logging):
        vault = temp_vault_no_logging

        prompts_dir = Path(vault.config["prompt_dir"])
        complex_template = {
            "id": "complex-template",
            "version": "1.0.0",
            "description": "Complex template",
            "template": "Name: {{ name }}, Age: {{ age }}, City: {{ city | default('Unknown') }}",
            "inputs": {
                "name": {"type": "string", "required": True},
                "age": {"type": "number", "required": True},
                "city": {"type": "string", "required": False}
            }
        }

        template_path = prompts_dir / "complex-template.yaml"
        template_path.write_text(yaml.safe_dump(complex_template))

        template = vault.get("complex-template")

        mock_result = ExecutionResult(
            output="Response",
            provider="openai",
            model="gpt-4",
            tokens_in=50,
            tokens_out=25,
            cost_usd=0.02,
            latency_ms=800
        )

        with patch.object(template, '_llm_client', None):
            with patch('dakora_server.core.vault.LLMClient') as mock_client_class:
                mock_client = Mock()
                mock_client.execute.return_value = mock_result
                mock_client_class.return_value = mock_client

                template.execute(
                    model="gpt-4",
                    name="John",
                    age=30,
                    temperature=0.5
                )

                call_args = mock_client.execute.call_args
                assert "Name: John, Age: 30, City: Unknown" in call_args[0][0]
                assert call_args[1]["temperature"] == 0.5

    def test_execute_with_messages_param(self, temp_vault_no_logging, mock_execution_result):
        vault = temp_vault_no_logging
        template = vault.get("test-template")

        with patch.object(template, '_llm_client', None):
            with patch('dakora_server.core.vault.LLMClient') as mock_client_class:
                mock_client = Mock()
                mock_client.execute.return_value = mock_execution_result
                mock_client_class.return_value = mock_client

                messages = [
                    {"role": "system", "content": "You are a helpful assistant"},
                    {"role": "user", "content": "Previous message"}
                ]

                template.execute(
                    model="gpt-4",
                    text="Sample text",
                    messages=messages
                )

                call_args = mock_client.execute.call_args
                assert call_args[1]["messages"] == messages


@pytest.mark.integration
class TestDatabaseMigration:
    """Integration tests for database migrations and logging (requires PostgreSQL)"""

    @pytest.fixture(autouse=True)
    def setup_test_db(self):
        """Create a fresh test database for each test"""
        # Get DATABASE_URL from environment or use default test database
        db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/dakora")

        # Create test engine
        engine = create_test_engine(db_url)

        try:
            # Ensure tables exist (created by migrations)
            metadata.create_all(engine)

            # Clear existing data for clean slate
            from dakora_server.core.database import get_connection, logs_table
            with get_connection(engine) as conn:
                conn.execute(logs_table.delete())
                conn.commit()

            yield engine
        finally:
            # Cleanup: just delete rows, don't drop tables
            from dakora_server.core.database import get_connection, logs_table
            try:
                with get_connection(engine) as conn:
                    conn.execute(logs_table.delete())
                    conn.commit()
            except Exception:
                pass
            engine.dispose()

    def test_migration_adds_llm_columns(self, setup_test_db):
        """Test that the logs table has all required LLM columns"""
        engine = setup_test_db

        # Initialize logger
        logger = Logger(engine)

        try:
            # Verify table structure by attempting to write with all columns
            logger.write(
                prompt_id="test-prompt",
                version="1.0.0",
                inputs={"text": "test"},
                output="test output",
                cost=None,
                latency_ms=1000,
                provider="openai",
                model="gpt-4",
                tokens_in=100,
                tokens_out=50,
                cost_usd=0.05
            )

            # Query to verify columns exist
            from dakora_server.core.database import get_connection
            from sqlalchemy import select, text

            with get_connection(engine) as conn:
                # Verify we can select all columns
                result = conn.execute(
                    text("""
                        SELECT prompt_id, version, provider, model,
                               tokens_in, tokens_out, cost_usd
                        FROM logs
                        LIMIT 1
                    """)
                ).fetchone()

                assert result is not None
                assert result[0] == "test-prompt"
                assert result[1] == "1.0.0"
                assert result[2] == "openai"
                assert result[3] == "gpt-4"
                assert result[4] == 100
                assert result[5] == 50
                assert result[6] == 0.05
        finally:
            logger.close()

    def test_logger_write_with_llm_metadata(self, setup_test_db):
        """Test that logger correctly writes LLM metadata to PostgreSQL"""
        engine = setup_test_db

        logger = Logger(engine)

        try:
            logger.write(
                prompt_id="test-prompt",
                version="1.0.0",
                inputs={"text": "test"},
                output="test output",
                cost=None,
                latency_ms=1000,
                provider="openai",
                model="gpt-4",
                tokens_in=100,
                tokens_out=50,
                cost_usd=0.05
            )

            # Read and verify
            from dakora_server.core.database import get_connection, logs_table
            from sqlalchemy import select

            with get_connection(engine) as conn:
                result = conn.execute(select(logs_table)).fetchone()

                assert result.prompt_id == "test-prompt"
                assert result.version == "1.0.0"
                assert result.provider == "openai"
                assert result.model == "gpt-4"
                assert result.tokens_in == 100
                assert result.tokens_out == 50
                assert result.cost_usd == 0.05
        finally:
            logger.close()