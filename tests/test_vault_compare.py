import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import yaml
import pytest
import sqlite3
import asyncio
import gc
import time

from dakora.vault import Vault
from dakora.llm.models import ExecutionResult, ComparisonResult
from dakora.exceptions import ValidationError


@pytest.fixture
def temp_vault_with_logging():
    with tempfile.TemporaryDirectory() as tmpdir:
        prompts_dir = Path(tmpdir) / "prompts"
        prompts_dir.mkdir()

        test_template = {
            "id": "test-template",
            "version": "1.0.0",
            "description": "Test template for comparison",
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
            "description": "Test template for comparison",
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
def mock_comparison_result():
    return ComparisonResult(
        results=[
            ExecutionResult(
                output="GPT-4 summary",
                provider="openai",
                model="gpt-4",
                tokens_in=100,
                tokens_out=50,
                cost_usd=0.05,
                latency_ms=1200
            ),
            ExecutionResult(
                output="Claude summary",
                provider="anthropic",
                model="claude-3-opus",
                tokens_in=105,
                tokens_out=48,
                cost_usd=0.04,
                latency_ms=900
            ),
            ExecutionResult(
                output="Gemini summary",
                provider="google",
                model="gemini-pro",
                tokens_in=98,
                tokens_out=52,
                cost_usd=0.02,
                latency_ms=1500
            )
        ],
        total_cost_usd=0.11,
        total_tokens_in=303,
        total_tokens_out=150,
        total_time_ms=1500,
        successful_count=3,
        failed_count=0
    )


class TestTemplateHandleCompare:
    def test_compare_basic_success(self, temp_vault_no_logging, mock_comparison_result):
        vault = temp_vault_no_logging
        template = vault.get("test-template")

        with patch.object(template, '_llm_client', None):
            with patch('dakora.vault.LLMClient') as mock_client_class:
                mock_client = Mock()
                mock_client.compare = AsyncMock(return_value=mock_comparison_result)
                mock_client_class.return_value = mock_client

                result = asyncio.run(template.compare(
                    models=["gpt-4", "claude-3-opus", "gemini-pro"],
                    text="Sample text to summarize"
                ))

                assert result == mock_comparison_result
                assert len(result.results) == 3
                assert result.total_cost_usd == 0.11
                assert result.total_tokens_in == 303
                assert result.total_tokens_out == 150
                assert result.successful_count == 3
                assert result.failed_count == 0

                mock_client.compare.assert_called_once()
                call_args = mock_client.compare.call_args
                assert call_args[0][0] == "Summarize this text: Sample text to summarize"
                assert call_args[0][1] == ["gpt-4", "claude-3-opus", "gemini-pro"]

    def test_compare_with_llm_params(self, temp_vault_no_logging, mock_comparison_result):
        vault = temp_vault_no_logging
        template = vault.get("test-template")

        with patch.object(template, '_llm_client', None):
            with patch('dakora.vault.LLMClient') as mock_client_class:
                mock_client = Mock()
                mock_client.compare = AsyncMock(return_value=mock_comparison_result)
                mock_client_class.return_value = mock_client

                result = asyncio.run(template.compare(
                    models=["gpt-4", "claude-3-opus"],
                    text="Sample text",
                    temperature=0.7,
                    max_tokens=100
                ))

                assert result == mock_comparison_result

                call_args = mock_client.compare.call_args
                assert call_args[1]["temperature"] == 0.7
                assert call_args[1]["max_tokens"] == 100

    def test_compare_with_logging(self, temp_vault_with_logging, mock_comparison_result):
        vault, tmpdir = temp_vault_with_logging
        template = vault.get("test-template")

        with patch.object(template, '_llm_client', None):
            with patch('dakora.vault.LLMClient') as mock_client_class:
                mock_client = Mock()
                mock_client.compare = AsyncMock(return_value=mock_comparison_result)
                mock_client_class.return_value = mock_client

                result = asyncio.run(template.compare(
                    models=["gpt-4", "claude-3-opus", "gemini-pro"],
                    text="Sample text"
                ))

                assert result == mock_comparison_result

                db_path = Path(tmpdir) / "dakora.db"
                assert db_path.exists()

                with sqlite3.connect(db_path) as con:
                    cursor = con.execute("SELECT * FROM logs")
                    rows = cursor.fetchall()
                    assert len(rows) == 3

                    assert rows[0][7] == "openai"
                    assert rows[0][8] == "gpt-4"
                    assert rows[1][7] == "anthropic"
                    assert rows[1][8] == "claude-3-opus"
                    assert rows[2][7] == "google"
                    assert rows[2][8] == "gemini-pro"

    def test_compare_partial_failure(self, temp_vault_no_logging):
        vault = temp_vault_no_logging
        template = vault.get("test-template")

        partial_result = ComparisonResult(
            results=[
                ExecutionResult(
                    output="GPT-4 summary",
                    provider="openai",
                    model="gpt-4",
                    tokens_in=100,
                    tokens_out=50,
                    cost_usd=0.05,
                    latency_ms=1200
                ),
                ExecutionResult(
                    output="",
                    provider="unknown",
                    model="claude-3-opus",
                    tokens_in=0,
                    tokens_out=0,
                    cost_usd=0.0,
                    latency_ms=500,
                    error="Invalid API key for model 'claude-3-opus'"
                ),
                ExecutionResult(
                    output="Gemini summary",
                    provider="google",
                    model="gemini-pro",
                    tokens_in=98,
                    tokens_out=52,
                    cost_usd=0.02,
                    latency_ms=1500
                )
            ],
            total_cost_usd=0.07,
            total_tokens_in=198,
            total_tokens_out=102,
            total_time_ms=1500,
            successful_count=2,
            failed_count=1
        )

        with patch.object(template, '_llm_client', None):
            with patch('dakora.vault.LLMClient') as mock_client_class:
                mock_client = Mock()
                mock_client.compare = AsyncMock(return_value=partial_result)
                mock_client_class.return_value = mock_client

                result = asyncio.run(template.compare(
                    models=["gpt-4", "claude-3-opus", "gemini-pro"],
                    text="Sample text"
                ))

                assert result.successful_count == 2
                assert result.failed_count == 1
                assert result.results[1].error is not None
                assert "Invalid API key" in result.results[1].error

    def test_compare_all_failures(self, temp_vault_no_logging):
        vault = temp_vault_no_logging
        template = vault.get("test-template")

        failure_result = ComparisonResult(
            results=[
                ExecutionResult(
                    output="",
                    provider="unknown",
                    model="gpt-4",
                    tokens_in=0,
                    tokens_out=0,
                    cost_usd=0.0,
                    latency_ms=100,
                    error="Rate limit exceeded"
                ),
                ExecutionResult(
                    output="",
                    provider="unknown",
                    model="claude-3-opus",
                    tokens_in=0,
                    tokens_out=0,
                    cost_usd=0.0,
                    latency_ms=100,
                    error="Invalid API key"
                )
            ],
            total_cost_usd=0.0,
            total_tokens_in=0,
            total_tokens_out=0,
            total_time_ms=100,
            successful_count=0,
            failed_count=2
        )

        with patch.object(template, '_llm_client', None):
            with patch('dakora.vault.LLMClient') as mock_client_class:
                mock_client = Mock()
                mock_client.compare = AsyncMock(return_value=failure_result)
                mock_client_class.return_value = mock_client

                result = asyncio.run(template.compare(
                    models=["gpt-4", "claude-3-opus"],
                    text="Sample text"
                ))

                assert result.successful_count == 0
                assert result.failed_count == 2
                assert all(r.error is not None for r in result.results)

    def test_compare_validation_error(self, temp_vault_no_logging):
        vault = temp_vault_no_logging
        template = vault.get("test-template")

        with pytest.raises(ValidationError):
            asyncio.run(template.compare(models=["gpt-4", "claude-3-opus"]))

    def test_compare_single_model(self, temp_vault_no_logging):
        vault = temp_vault_no_logging
        template = vault.get("test-template")

        single_result = ComparisonResult(
            results=[
                ExecutionResult(
                    output="GPT-4 summary",
                    provider="openai",
                    model="gpt-4",
                    tokens_in=100,
                    tokens_out=50,
                    cost_usd=0.05,
                    latency_ms=1200
                )
            ],
            total_cost_usd=0.05,
            total_tokens_in=100,
            total_tokens_out=50,
            total_time_ms=1200,
            successful_count=1,
            failed_count=0
        )

        with patch.object(template, '_llm_client', None):
            with patch('dakora.vault.LLMClient') as mock_client_class:
                mock_client = Mock()
                mock_client.compare = AsyncMock(return_value=single_result)
                mock_client_class.return_value = mock_client

                result = asyncio.run(template.compare(models=["gpt-4"], text="Sample text"))

                assert len(result.results) == 1
                assert result.successful_count == 1

    def test_compare_preserves_model_order(self, temp_vault_no_logging):
        vault = temp_vault_no_logging
        template = vault.get("test-template")

        ordered_result = ComparisonResult(
            results=[
                ExecutionResult(
                    output="Gemini summary",
                    provider="google",
                    model="gemini-pro",
                    tokens_in=98,
                    tokens_out=52,
                    cost_usd=0.02,
                    latency_ms=1500
                ),
                ExecutionResult(
                    output="GPT-4 summary",
                    provider="openai",
                    model="gpt-4",
                    tokens_in=100,
                    tokens_out=50,
                    cost_usd=0.05,
                    latency_ms=1200
                ),
                ExecutionResult(
                    output="Claude summary",
                    provider="anthropic",
                    model="claude-3-opus",
                    tokens_in=105,
                    tokens_out=48,
                    cost_usd=0.04,
                    latency_ms=900
                )
            ],
            total_cost_usd=0.11,
            total_tokens_in=303,
            total_tokens_out=150,
            total_time_ms=1500,
            successful_count=3,
            failed_count=0
        )

        with patch.object(template, '_llm_client', None):
            with patch('dakora.vault.LLMClient') as mock_client_class:
                mock_client = Mock()
                mock_client.compare = AsyncMock(return_value=ordered_result)
                mock_client_class.return_value = mock_client

                result = asyncio.run(template.compare(
                    models=["gemini-pro", "gpt-4", "claude-3-opus"],
                    text="Sample text"
                ))

                assert result.results[0].model == "gemini-pro"
                assert result.results[1].model == "gpt-4"
                assert result.results[2].model == "claude-3-opus"

    def test_compare_client_reuse(self, temp_vault_no_logging, mock_comparison_result):
        vault = temp_vault_no_logging
        template = vault.get("test-template")

        with patch.object(template, '_llm_client', None):
            with patch('dakora.vault.LLMClient') as mock_client_class:
                mock_client = Mock()
                mock_client.compare = AsyncMock(return_value=mock_comparison_result)
                mock_client_class.return_value = mock_client

                asyncio.run(template.compare(models=["gpt-4", "claude-3-opus"], text="First comparison"))
                asyncio.run(template.compare(models=["gpt-4", "gemini-pro"], text="Second comparison"))

                assert mock_client_class.call_count == 1
                assert mock_client.compare.call_count == 2

    def test_compare_with_complex_template(self, temp_vault_no_logging):
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

        mock_result = ComparisonResult(
            results=[
                ExecutionResult(
                    output="Response 1",
                    provider="openai",
                    model="gpt-4",
                    tokens_in=50,
                    tokens_out=25,
                    cost_usd=0.02,
                    latency_ms=800
                ),
                ExecutionResult(
                    output="Response 2",
                    provider="anthropic",
                    model="claude-3-opus",
                    tokens_in=52,
                    tokens_out=26,
                    cost_usd=0.03,
                    latency_ms=700
                )
            ],
            total_cost_usd=0.05,
            total_tokens_in=102,
            total_tokens_out=51,
            total_time_ms=800,
            successful_count=2,
            failed_count=0
        )

        with patch.object(template, '_llm_client', None):
            with patch('dakora.vault.LLMClient') as mock_client_class:
                mock_client = Mock()
                mock_client.compare = AsyncMock(return_value=mock_result)
                mock_client_class.return_value = mock_client

                asyncio.run(template.compare(
                    models=["gpt-4", "claude-3-opus"],
                    name="John",
                    age=30,
                    temperature=0.5
                ))

                call_args = mock_client.compare.call_args
                assert "Name: John, Age: 30, City: Unknown" in call_args[0][0]
                assert call_args[1]["temperature"] == 0.5


class TestComparisonResultModel:
    def test_comparison_result_creation(self):
        result = ComparisonResult(
            results=[],
            total_cost_usd=0.0,
            total_tokens_in=0,
            total_tokens_out=0,
            total_time_ms=0,
            successful_count=0,
            failed_count=0
        )
        assert result.results == []
        assert result.total_cost_usd == 0.0

    def test_comparison_result_validation(self):
        with pytest.raises(Exception):
            ComparisonResult(
                results=[],
                total_cost_usd=-1.0,
                total_tokens_in=0,
                total_tokens_out=0,
                total_time_ms=0,
                successful_count=0,
                failed_count=0
            )