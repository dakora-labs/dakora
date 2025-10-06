import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import yaml
import pytest
from typer.testing import CliRunner

from dakora.cli import app
from dakora.llm.models import ExecutionResult
from dakora.exceptions import ValidationError, APIKeyError, RateLimitError, ModelNotFoundError, LLMError


@pytest.fixture
def temp_project():
    with tempfile.TemporaryDirectory() as tmpdir:
        prompts_dir = Path(tmpdir) / "prompts"
        prompts_dir.mkdir()

        summarizer_template = {
            "id": "summarizer",
            "version": "1.0.0",
            "description": "Summarize text",
            "template": "Summarize this: {{ input_text }}",
            "inputs": {
                "input_text": {
                    "type": "string",
                    "required": True
                }
            }
        }

        chatbot_template = {
            "id": "chatbot",
            "version": "1.0.0",
            "description": "Chat assistant",
            "template": "User: {{ message }}\nAssistant:",
            "inputs": {
                "message": {
                    "type": "string",
                    "required": True
                }
            }
        }

        (prompts_dir / "summarizer.yaml").write_text(yaml.safe_dump(summarizer_template))
        (prompts_dir / "chatbot.yaml").write_text(yaml.safe_dump(chatbot_template))

        config = {
            "registry": "local",
            "prompt_dir": str(prompts_dir),
            "logging": {
                "enabled": False
            }
        }

        config_path = Path(tmpdir) / "dakora.yaml"
        config_path.write_text(yaml.safe_dump(config))

        yield tmpdir, config_path


@pytest.fixture
def mock_execution_result():
    return ExecutionResult(
        output="This is a test response from the LLM.",
        provider="openai",
        model="gpt-4",
        tokens_in=20,
        tokens_out=10,
        cost_usd=0.0045,
        latency_ms=1234
    )


@pytest.fixture
def runner():
    return CliRunner()


class TestCliRun:
    def test_run_basic_success(self, temp_project, mock_execution_result, runner):
        tmpdir, config_path = temp_project

        with patch('dakora.vault.Vault') as mock_vault_class:
            mock_vault = Mock()
            mock_template = Mock()
            mock_template.spec.inputs = {"input_text": {"type": "string", "required": True}}
            mock_template.execute.return_value = mock_execution_result
            mock_vault.get.return_value = mock_template
            mock_vault_class.return_value = mock_vault

            result = runner.invoke(app, [
                "run", "summarizer",
                "--model", "gpt-4",
                "--config", str(config_path),
                "--input-text", "Test article content"
            ])

            assert result.exit_code == 0
            assert "gpt-4" in result.stdout
            assert "openai" in result.stdout
            assert "$0.0045" in result.stdout
            assert "1,234 ms" in result.stdout
            assert "20 → 10" in result.stdout
            assert "This is a test response from the LLM." in result.stdout

            mock_template.execute.assert_called_once()
            call_kwargs = mock_template.execute.call_args[1]
            assert call_kwargs["model"] == "gpt-4"
            assert call_kwargs["input_text"] == "Test article content"

    def test_run_with_temperature(self, temp_project, mock_execution_result, runner):
        tmpdir, config_path = temp_project

        with patch('dakora.vault.Vault') as mock_vault_class:
            mock_vault = Mock()
            mock_template = Mock()
            mock_template.spec.inputs = {"input_text": {"type": "string", "required": True}}
            mock_template.execute.return_value = mock_execution_result
            mock_vault.get.return_value = mock_template
            mock_vault_class.return_value = mock_vault

            result = runner.invoke(app, [
                "run", "summarizer",
                "--model", "gpt-4",
                "--config", str(config_path),
                "--input-text", "Test content",
                "--temperature", "0.7"
            ])

            assert result.exit_code == 0

            call_kwargs = mock_template.execute.call_args[1]
            assert call_kwargs["temperature"] == 0.7

    def test_run_with_max_tokens_and_top_p(self, temp_project, mock_execution_result, runner):
        tmpdir, config_path = temp_project

        with patch('dakora.vault.Vault') as mock_vault_class:
            mock_vault = Mock()
            mock_template = Mock()
            mock_template.spec.inputs = {"input_text": {"type": "string", "required": True}}
            mock_template.execute.return_value = mock_execution_result
            mock_vault.get.return_value = mock_template
            mock_vault_class.return_value = mock_vault

            result = runner.invoke(app, [
                "run", "summarizer",
                "--model", "gpt-4",
                "--config", str(config_path),
                "--input-text", "Test content",
                "--max-tokens", "100",
                "--top-p", "0.9"
            ])

            assert result.exit_code == 0

            call_kwargs = mock_template.execute.call_args[1]
            assert call_kwargs["max_tokens"] == 100
            assert call_kwargs["top_p"] == 0.9

    def test_run_json_output(self, temp_project, mock_execution_result, runner):
        tmpdir, config_path = temp_project

        with patch('dakora.vault.Vault') as mock_vault_class:
            mock_vault = Mock()
            mock_template = Mock()
            mock_template.spec.inputs = {"input_text": {"type": "string", "required": True}}
            mock_template.execute.return_value = mock_execution_result
            mock_vault.get.return_value = mock_template
            mock_vault_class.return_value = mock_vault

            result = runner.invoke(app, [
                "run", "summarizer",
                "--model", "gpt-4",
                "--config", str(config_path),
                "--input-text", "Test content",
                "--json"
            ])

            assert result.exit_code == 0
            assert '"output": "This is a test response from the LLM."' in result.stdout
            assert '"provider": "openai"' in result.stdout
            assert '"model": "gpt-4"' in result.stdout
            assert '"tokens_in": 20' in result.stdout
            assert '"tokens_out": 10' in result.stdout

    def test_run_quiet_output(self, temp_project, mock_execution_result, runner):
        tmpdir, config_path = temp_project

        with patch('dakora.vault.Vault') as mock_vault_class:
            mock_vault = Mock()
            mock_template = Mock()
            mock_template.spec.inputs = {"input_text": {"type": "string", "required": True}}
            mock_template.execute.return_value = mock_execution_result
            mock_vault.get.return_value = mock_template
            mock_vault_class.return_value = mock_vault

            result = runner.invoke(app, [
                "run", "summarizer",
                "--model", "gpt-4",
                "--config", str(config_path),
                "--input-text", "Test content",
                "--quiet"
            ])

            assert result.exit_code == 0
            assert result.stdout.strip() == "This is a test response from the LLM."
            assert "gpt-4" not in result.stdout
            assert "openai" not in result.stdout

    def test_run_missing_required_input(self, temp_project, runner):
        tmpdir, config_path = temp_project

        with patch('dakora.vault.Vault') as mock_vault_class:
            mock_vault = Mock()
            mock_template = Mock()
            mock_template.spec.inputs = {"input_text": {"type": "string", "required": True}}
            mock_vault.get.return_value = mock_template
            mock_vault_class.return_value = mock_vault

            result = runner.invoke(app, [
                "run", "summarizer",
                "--model", "gpt-4",
                "--config", str(config_path)
            ])

            assert result.exit_code == 1
            assert "Missing required inputs: input_text" in result.stdout

    def test_run_template_not_found(self, temp_project, runner):
        tmpdir, config_path = temp_project

        with patch('dakora.vault.Vault') as mock_vault_class:
            from dakora.exceptions import TemplateNotFound
            mock_vault = Mock()
            mock_vault.get.side_effect = TemplateNotFound("Template not found")
            mock_vault_class.return_value = mock_vault

            result = runner.invoke(app, [
                "run", "nonexistent",
                "--model", "gpt-4",
                "--config", str(config_path),
                "--input-text", "Test"
            ])

            assert result.exit_code == 1
            assert "Template 'nonexistent' not found" in result.stdout

    def test_run_config_not_found(self, runner):
        result = runner.invoke(app, [
            "run", "summarizer",
            "--model", "gpt-4",
            "--config", "/nonexistent/dakora.yaml",
            "--input-text", "Test"
        ])

        assert result.exit_code == 1
        assert "Config file not found" in result.stdout

    def test_run_api_key_error(self, temp_project, runner):
        tmpdir, config_path = temp_project

        with patch('dakora.vault.Vault') as mock_vault_class:
            mock_vault = Mock()
            mock_template = Mock()
            mock_template.spec.inputs = {"input_text": {"type": "string", "required": True}}
            mock_template.execute.side_effect = APIKeyError("Invalid API key")
            mock_vault.get.return_value = mock_template
            mock_vault_class.return_value = mock_vault

            result = runner.invoke(app, [
                "run", "summarizer",
                "--model", "gpt-4",
                "--config", str(config_path),
                "--input-text", "Test"
            ])

            assert result.exit_code == 1
            assert "API key error" in result.stdout
            assert "OPENAI_API_KEY" in result.stdout or "ANTHROPIC_API_KEY" in result.stdout

    def test_run_rate_limit_error(self, temp_project, runner):
        tmpdir, config_path = temp_project

        with patch('dakora.vault.Vault') as mock_vault_class:
            mock_vault = Mock()
            mock_template = Mock()
            mock_template.spec.inputs = {"input_text": {"type": "string", "required": True}}
            mock_template.execute.side_effect = RateLimitError("Rate limit exceeded")
            mock_vault.get.return_value = mock_template
            mock_vault_class.return_value = mock_vault

            result = runner.invoke(app, [
                "run", "summarizer",
                "--model", "gpt-4",
                "--config", str(config_path),
                "--input-text", "Test"
            ])

            assert result.exit_code == 1
            assert "Rate limit exceeded" in result.stdout

    def test_run_model_not_found_error(self, temp_project, runner):
        tmpdir, config_path = temp_project

        with patch('dakora.vault.Vault') as mock_vault_class:
            mock_vault = Mock()
            mock_template = Mock()
            mock_template.spec.inputs = {"input_text": {"type": "string", "required": True}}
            mock_template.execute.side_effect = ModelNotFoundError("Model not found")
            mock_vault.get.return_value = mock_template
            mock_vault_class.return_value = mock_vault

            result = runner.invoke(app, [
                "run", "summarizer",
                "--model", "invalid-model",
                "--config", str(config_path),
                "--input-text", "Test"
            ])

            assert result.exit_code == 1
            assert "Model not found" in result.stdout

    def test_run_validation_error(self, temp_project, runner):
        tmpdir, config_path = temp_project

        with patch('dakora.vault.Vault') as mock_vault_class:
            mock_vault = Mock()
            mock_template = Mock()
            mock_template.spec.inputs = {"input_text": {"type": "string", "required": True}}
            mock_template.execute.side_effect = ValidationError("Invalid input type")
            mock_vault.get.return_value = mock_template
            mock_vault_class.return_value = mock_vault

            result = runner.invoke(app, [
                "run", "summarizer",
                "--model", "gpt-4",
                "--config", str(config_path),
                "--input-text", "Test"
            ])

            assert result.exit_code == 1
            assert "Validation error" in result.stdout

    def test_run_with_custom_llm_param(self, temp_project, mock_execution_result, runner):
        tmpdir, config_path = temp_project

        with patch('dakora.vault.Vault') as mock_vault_class:
            mock_vault = Mock()
            mock_template = Mock()
            mock_template.spec.inputs = {"input_text": {"type": "string", "required": True}}
            mock_template.execute.return_value = mock_execution_result
            mock_vault.get.return_value = mock_template
            mock_vault_class.return_value = mock_vault

            result = runner.invoke(app, [
                "run", "summarizer",
                "--model", "gpt-5-nano",
                "--config", str(config_path),
                "--input-text", "Test content",
                "--reasoning", '{"effort": "medium"}'
            ])

            assert result.exit_code == 0

            call_kwargs = mock_template.execute.call_args[1]
            assert "reasoning" in call_kwargs
            assert call_kwargs["reasoning"] == {"effort": "medium"}

    def test_run_short_model_flag(self, temp_project, mock_execution_result, runner):
        tmpdir, config_path = temp_project

        with patch('dakora.vault.Vault') as mock_vault_class:
            mock_vault = Mock()
            mock_template = Mock()
            mock_template.spec.inputs = {"input_text": {"type": "string", "required": True}}
            mock_template.execute.return_value = mock_execution_result
            mock_vault.get.return_value = mock_template
            mock_vault_class.return_value = mock_vault

            result = runner.invoke(app, [
                "run", "summarizer",
                "-m", "gpt-4",
                "--config", str(config_path),
                "--input-text", "Test"
            ])

            assert result.exit_code == 0
            mock_template.execute.assert_called_once()

    def test_run_with_zero_cost(self, temp_project, runner):
        tmpdir, config_path = temp_project

        zero_cost_result = ExecutionResult(
            output="Response from free model",
            provider="ollama",
            model="llama3",
            tokens_in=15,
            tokens_out=8,
            cost_usd=0.0,
            latency_ms=500
        )

        with patch('dakora.vault.Vault') as mock_vault_class:
            mock_vault = Mock()
            mock_template = Mock()
            mock_template.spec.inputs = {"input_text": {"type": "string", "required": True}}
            mock_template.execute.return_value = zero_cost_result
            mock_vault.get.return_value = mock_template
            mock_vault_class.return_value = mock_vault

            result = runner.invoke(app, [
                "run", "summarizer",
                "--model", "ollama/llama3",
                "--config", str(config_path),
                "--input-text", "Test"
            ])

            assert result.exit_code == 0
            assert "$0.0000" in result.stdout

    def test_run_with_high_latency(self, temp_project, runner):
        tmpdir, config_path = temp_project

        high_latency_result = ExecutionResult(
            output="Slow response",
            provider="openai",
            model="gpt-4",
            tokens_in=100,
            tokens_out=50,
            cost_usd=0.05,
            latency_ms=25000
        )

        with patch('dakora.vault.Vault') as mock_vault_class:
            mock_vault = Mock()
            mock_template = Mock()
            mock_template.spec.inputs = {"input_text": {"type": "string", "required": True}}
            mock_template.execute.return_value = high_latency_result
            mock_vault.get.return_value = mock_template
            mock_vault_class.return_value = mock_vault

            result = runner.invoke(app, [
                "run", "summarizer",
                "--model", "gpt-4",
                "--config", str(config_path),
                "--input-text", "Test"
            ])

            assert result.exit_code == 0
            assert "25.0s" in result.stdout