#!/usr/bin/env python3

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock
import yaml
import pytest
from typer.testing import CliRunner

from dakora.cli import app
from dakora.llm.models import ExecutionResult, ComparisonResult
from dakora.exceptions import (
    ValidationError,
    RenderError,
    APIKeyError,
    RateLimitError,
    ModelNotFoundError,
    LLMError
)

runner = CliRunner()


@pytest.fixture
def temp_project():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        prompts_dir = tmpdir / "prompts"
        prompts_dir.mkdir()

        test_template = {
            "id": "test-compare",
            "version": "1.0.0",
            "description": "Test template for comparison",
            "template": "Summarize: {{ text }}",
            "inputs": {
                "text": {
                    "type": "string",
                    "required": True
                }
            }
        }

        (prompts_dir / "test-compare.yaml").write_text(yaml.safe_dump(test_template))

        config = {
            "registry": "local",
            "prompt_dir": str(prompts_dir),
            "logging": {
                "enabled": False
            }
        }

        config_path = tmpdir / "dakora.yaml"
        config_path.write_text(yaml.safe_dump(config))

        yield str(config_path)


def test_compare_basic(temp_project):
    mock_result1 = ExecutionResult(
        output="This is a summary from GPT-4",
        provider="openai",
        model="gpt-4",
        tokens_in=10,
        tokens_out=20,
        cost_usd=0.001,
        latency_ms=500
    )

    mock_result2 = ExecutionResult(
        output="This is a summary from Claude",
        provider="anthropic",
        model="claude-3-opus",
        tokens_in=10,
        tokens_out=22,
        cost_usd=0.002,
        latency_ms=600
    )

    mock_comparison = ComparisonResult(
        results=[mock_result1, mock_result2],
        total_cost_usd=0.003,
        total_tokens_in=20,
        total_tokens_out=42,
        successful_count=2,
        total_time_ms=600,
        failed_count=0
    )

    with patch('dakora.vault.TemplateHandle.compare', return_value=mock_comparison):
        result = runner.invoke(app, [
            'compare',
            'test-compare',
            '--config', temp_project,
            '--models', 'gpt-4,claude-3-opus',
            '--text', 'Test article content'
        ])

    assert result.exit_code == 0
    assert "gpt-4" in result.stdout
    assert "claude-3-opus" in result.stdout
    assert "$0.003" in result.stdout
    assert "Success: 2/2" in result.stdout
    assert "✅" in result.stdout


def test_compare_json_output(temp_project):
    mock_result = ExecutionResult(
        output="JSON test output",
        provider="openai",
        model="gpt-4",
        tokens_in=10,
        tokens_out=20,
        cost_usd=0.001,
        latency_ms=500
    )

    mock_comparison = ComparisonResult(
        results=[mock_result],
        total_cost_usd=0.001,
        total_tokens_in=10,
        total_tokens_out=20,
        successful_count=1,
        total_time_ms=600,
        failed_count=0
    )

    with patch('dakora.vault.TemplateHandle.compare', return_value=mock_comparison):
        result = runner.invoke(app, [
            'compare',
            'test-compare',
            '--config', temp_project,
            '--models', 'gpt-4',
            '--text', 'Test',
            '--json'
        ])

    assert result.exit_code == 0
    output = json.loads(result.stdout)
    assert output['total_cost_usd'] == 0.001
    assert output['successful_count'] == 1
    assert output['failed_count'] == 0
    assert len(output['results']) == 1
    assert output['results'][0]['model'] == 'gpt-4'
    assert output['results'][0]['output'] == 'JSON test output'


def test_compare_verbose_output(temp_project):
    mock_result1 = ExecutionResult(
        output="This is a detailed response from GPT-4 with multiple sentences that should be displayed in full.",
        provider="openai",
        model="gpt-4",
        tokens_in=10,
        tokens_out=20,
        cost_usd=0.001,
        latency_ms=500
    )

    mock_result2 = ExecutionResult(
        output="This is a detailed response from Claude with multiple sentences that should be displayed in full.",
        provider="anthropic",
        model="claude-3-opus",
        tokens_in=10,
        tokens_out=22,
        cost_usd=0.002,
        latency_ms=600
    )

    mock_comparison = ComparisonResult(
        results=[mock_result1, mock_result2],
        total_cost_usd=0.003,
        total_tokens_in=20,
        total_tokens_out=42,
        successful_count=2,
        total_time_ms=600,
        failed_count=0
    )

    with patch('dakora.vault.TemplateHandle.compare', return_value=mock_comparison):
        result = runner.invoke(app, [
            'compare',
            'test-compare',
            '--config', temp_project,
            '--models', 'gpt-4,claude-3-opus',
            '--text', 'Test',
            '--verbose'
        ])

    assert result.exit_code == 0
    assert "This is a detailed response from GPT-4" in result.stdout
    assert "This is a detailed response from Claude" in result.stdout
    assert "✅ gpt-4" in result.stdout
    assert "✅ claude-3-opus" in result.stdout
    assert "Total Cost: $0.003" in result.stdout
    assert "Success Rate: 2/2" in result.stdout


def test_compare_with_failure(temp_project):
    mock_result1 = ExecutionResult(
        output="Success response",
        provider="openai",
        model="gpt-4",
        tokens_in=10,
        tokens_out=20,
        cost_usd=0.001,
        latency_ms=500
    )

    mock_result2 = ExecutionResult(
        output="",
        provider="anthropic",
        model="claude-3-opus",
        tokens_in=0,
        tokens_out=0,
        cost_usd=0.0,
        latency_ms=0,
        error="API key not found"
    )

    mock_comparison = ComparisonResult(
        results=[mock_result1, mock_result2],
        total_cost_usd=0.001,
        total_tokens_in=10,
        total_tokens_out=20,
        successful_count=1,
        total_time_ms=600,
        failed_count=1
    )

    with patch('dakora.vault.TemplateHandle.compare', return_value=mock_comparison):
        result = runner.invoke(app, [
            'compare',
            'test-compare',
            '--config', temp_project,
            '--models', 'gpt-4,claude-3-opus',
            '--text', 'Test'
        ])

    assert result.exit_code == 0
    assert "✅" in result.stdout
    assert "❌" in result.stdout
    assert "Success: 1/2" in result.stdout
    assert "Some models failed" in result.stdout


def test_compare_all_failures(temp_project):
    mock_result1 = ExecutionResult(
        output="",
        provider="openai",
        model="gpt-4",
        tokens_in=0,
        tokens_out=0,
        cost_usd=0.0,
        latency_ms=0,
        error="Rate limit exceeded"
    )

    mock_result2 = ExecutionResult(
        output="",
        provider="anthropic",
        model="claude-3-opus",
        tokens_in=0,
        tokens_out=0,
        cost_usd=0.0,
        latency_ms=0,
        error="Invalid API key"
    )

    mock_comparison = ComparisonResult(
        results=[mock_result1, mock_result2],
        total_cost_usd=0.0,
        total_tokens_in=0,
        total_tokens_out=0,
        successful_count=0,
        total_time_ms=600,
        failed_count=2
    )

    with patch('dakora.vault.TemplateHandle.compare', return_value=mock_comparison):
        result = runner.invoke(app, [
            'compare',
            'test-compare',
            '--config', temp_project,
            '--models', 'gpt-4,claude-3-opus',
            '--text', 'Test'
        ])

    assert result.exit_code == 0
    assert "Success: 0/2" in result.stdout
    assert "❌" in result.stdout


def test_compare_verbose_with_failures(temp_project):
    mock_result1 = ExecutionResult(
        output="Success",
        provider="openai",
        model="gpt-4",
        tokens_in=10,
        tokens_out=20,
        cost_usd=0.001,
        latency_ms=500
    )

    mock_result2 = ExecutionResult(
        output="",
        provider="anthropic",
        model="claude-3-opus",
        tokens_in=0,
        tokens_out=0,
        cost_usd=0.0,
        latency_ms=0,
        error="Model not available"
    )

    mock_comparison = ComparisonResult(
        results=[mock_result1, mock_result2],
        total_cost_usd=0.001,
        total_tokens_in=10,
        total_tokens_out=20,
        successful_count=1,
        total_time_ms=600,
        failed_count=1
    )

    with patch('dakora.vault.TemplateHandle.compare', return_value=mock_comparison):
        result = runner.invoke(app, [
            'compare',
            'test-compare',
            '--config', temp_project,
            '--models', 'gpt-4,claude-3-opus',
            '--text', 'Test',
            '--verbose'
        ])

    assert result.exit_code == 0
    assert "✅ gpt-4" in result.stdout
    assert "❌ claude-3-opus" in result.stdout
    assert "Error: Model not available" in result.stdout
    assert "Success Rate: 1/2" in result.stdout


def test_compare_missing_config(temp_project):
    result = runner.invoke(app, [
        'compare',
        'test-compare',
        '--config', '/nonexistent/dakora.yaml',
        '--models', 'gpt-4',
        '--text', 'Test'
    ])

    assert result.exit_code == 1
    output = result.stdout + result.stderr
    assert "Config file not found" in output


def test_compare_template_not_found(temp_project):
    result = runner.invoke(app, [
        'compare',
        'nonexistent-template',
        '--config', temp_project,
        '--models', 'gpt-4',
        '--text', 'Test'
    ])

    assert result.exit_code == 1
    output = result.stdout + result.stderr
    assert "Template 'nonexistent-template' not found" in output


def test_compare_no_models_specified(temp_project):
    result = runner.invoke(app, [
        'compare',
        'test-compare',
        '--config', temp_project,
        '--models', '',
        '--text', 'Test'
    ])

    assert result.exit_code == 1
    output = result.stdout + result.stderr
    assert "No models specified" in output


def test_compare_missing_required_input(temp_project):
    result = runner.invoke(app, [
        'compare',
        'test-compare',
        '--config', temp_project,
        '--models', 'gpt-4,claude-3-opus'
    ])

    assert result.exit_code == 1
    output = result.stdout + result.stderr
    assert "Missing required inputs: text" in output


def test_compare_with_llm_params(temp_project):
    mock_result = ExecutionResult(
        output="Test output",
        provider="openai",
        model="gpt-4",
        tokens_in=10,
        tokens_out=20,
        cost_usd=0.001,
        latency_ms=500
    )

    mock_comparison = ComparisonResult(
        results=[mock_result],
        total_cost_usd=0.001,
        total_tokens_in=10,
        total_tokens_out=20,
        successful_count=1,
        total_time_ms=600,
        failed_count=0
    )

    with patch('dakora.vault.TemplateHandle.compare', return_value=mock_comparison) as mock_compare:
        result = runner.invoke(app, [
            'compare',
            'test-compare',
            '--config', temp_project,
            '--models', 'gpt-4',
            '--text', 'Test',
            '--temperature', '0.7',
            '--max-tokens', '100'
        ])

    assert result.exit_code == 0
    mock_compare.assert_called_once()
    call_kwargs = mock_compare.call_args.kwargs
    assert 'temperature' in call_kwargs
    assert call_kwargs['temperature'] == 0.7
    assert 'max_tokens' in call_kwargs
    assert call_kwargs['max_tokens'] == 100


def test_compare_validation_error(temp_project):
    with patch('dakora.vault.TemplateHandle.compare', side_effect=ValidationError("Invalid input")):
        result = runner.invoke(app, [
            'compare',
            'test-compare',
            '--config', temp_project,
            '--models', 'gpt-4',
            '--text', 'Test'
        ])

    assert result.exit_code == 1
    output = result.stdout + result.stderr
    assert "Validation error" in output


def test_compare_render_error(temp_project):
    with patch('dakora.vault.TemplateHandle.compare', side_effect=RenderError("Template error")):
        result = runner.invoke(app, [
            'compare',
            'test-compare',
            '--config', temp_project,
            '--models', 'gpt-4',
            '--text', 'Test'
        ])

    assert result.exit_code == 1
    output = result.stdout + result.stderr
    assert "Render error" in output


def test_compare_api_key_error(temp_project):
    with patch('dakora.vault.TemplateHandle.compare', side_effect=APIKeyError("Missing API key")):
        result = runner.invoke(app, [
            'compare',
            'test-compare',
            '--config', temp_project,
            '--models', 'gpt-4',
            '--text', 'Test'
        ])

    assert result.exit_code == 1
    output = result.stdout + result.stderr
    assert "API key error" in output
    assert "Set the required environment variable" in output


def test_compare_rate_limit_error(temp_project):
    with patch('dakora.vault.TemplateHandle.compare', side_effect=RateLimitError("Too many requests")):
        result = runner.invoke(app, [
            'compare',
            'test-compare',
            '--config', temp_project,
            '--models', 'gpt-4',
            '--text', 'Test'
        ])

    assert result.exit_code == 1
    output = result.stdout + result.stderr
    assert "Rate limit exceeded" in output


def test_compare_model_not_found_error(temp_project):
    with patch('dakora.vault.TemplateHandle.compare', side_effect=ModelNotFoundError("Model not available")):
        result = runner.invoke(app, [
            'compare',
            'test-compare',
            '--config', temp_project,
            '--models', 'gpt-4',
            '--text', 'Test'
        ])

    assert result.exit_code == 1
    output = result.stdout + result.stderr
    assert "Model not found" in output


def test_compare_llm_error(temp_project):
    with patch('dakora.vault.TemplateHandle.compare', side_effect=LLMError("LLM failed")):
        result = runner.invoke(app, [
            'compare',
            'test-compare',
            '--config', temp_project,
            '--models', 'gpt-4',
            '--text', 'Test'
        ])

    assert result.exit_code == 1
    output = result.stdout + result.stderr
    assert "LLM error" in output


def test_compare_unexpected_error(temp_project):
    with patch('dakora.vault.TemplateHandle.compare', side_effect=Exception("Unknown error")):
        result = runner.invoke(app, [
            'compare',
            'test-compare',
            '--config', temp_project,
            '--models', 'gpt-4',
            '--text', 'Test'
        ])

    assert result.exit_code == 1
    output = result.stdout + result.stderr
    assert "Unexpected error" in output


def test_compare_three_models(temp_project):
    mock_results = [
        ExecutionResult(
            output="GPT-4 response",
            provider="openai",
            model="gpt-4",
            tokens_in=10,
            tokens_out=20,
            cost_usd=0.001,
            latency_ms=500
        ),
        ExecutionResult(
            output="Claude response",
            provider="anthropic",
            model="claude-3-opus",
            tokens_in=10,
            tokens_out=22,
            cost_usd=0.002,
            latency_ms=600
        ),
        ExecutionResult(
            output="Gemini response",
            provider="google",
            model="gemini-pro",
            tokens_in=10,
            tokens_out=18,
            cost_usd=0.0005,
            latency_ms=400
        )
    ]

    mock_comparison = ComparisonResult(
        results=mock_results,
        total_cost_usd=0.0035,
        total_tokens_in=30,
        total_tokens_out=60,
        successful_count=3,
        total_time_ms=600,
        failed_count=0
    )

    with patch('dakora.vault.TemplateHandle.compare', return_value=mock_comparison):
        result = runner.invoke(app, [
            'compare',
            'test-compare',
            '--config', temp_project,
            '--models', 'gpt-4,claude-3-opus,gemini-pro',
            '--text', 'Test'
        ])

    assert result.exit_code == 0
    assert "gpt-4" in result.stdout
    assert "claude-3-opus" in result.stdout
    assert "gemini-pro" in result.stdout
    assert "Success: 3/3" in result.stdout
    assert "$0.0035" in result.stdout


def test_compare_long_model_names(temp_project):
    mock_result = ExecutionResult(
        output="Test response",
        provider="openai",
        model="gpt-4-turbo-preview-with-very-long-name",
        tokens_in=10,
        tokens_out=20,
        cost_usd=0.001,
        latency_ms=500
    )

    mock_comparison = ComparisonResult(
        results=[mock_result],
        total_cost_usd=0.001,
        total_tokens_in=10,
        total_tokens_out=20,
        successful_count=1,
        total_time_ms=600,
        failed_count=0
    )

    with patch('dakora.vault.TemplateHandle.compare', return_value=mock_comparison):
        result = runner.invoke(app, [
            'compare',
            'test-compare',
            '--config', temp_project,
            '--models', 'gpt-4-turbo-preview-with-very-long-name',
            '--text', 'Test'
        ])

    assert result.exit_code == 0
    assert "gpt-4-turbo-preview-with-very-long-name" in result.stdout


def test_compare_with_extra_args(temp_project):
    mock_result = ExecutionResult(
        output="Test output",
        provider="openai",
        model="gpt-4",
        tokens_in=10,
        tokens_out=20,
        cost_usd=0.001,
        latency_ms=500
    )

    mock_comparison = ComparisonResult(
        results=[mock_result],
        total_cost_usd=0.001,
        total_tokens_in=10,
        total_tokens_out=20,
        successful_count=1,
        total_time_ms=600,
        failed_count=0
    )

    with patch('dakora.vault.TemplateHandle.compare', return_value=mock_comparison) as mock_compare:
        result = runner.invoke(app, [
            'compare',
            'test-compare',
            '--config', temp_project,
            '--models', 'gpt-4',
            '--text', 'Test',
            '--custom-param', 'custom-value'
        ])

    assert result.exit_code == 0
    call_kwargs = mock_compare.call_args.kwargs
    assert 'custom_param' in call_kwargs
    assert call_kwargs['custom_param'] == 'custom-value'
