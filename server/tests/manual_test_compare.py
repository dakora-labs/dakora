#!/usr/bin/env python3
"""
Manual test for the compare CLI command.
This demonstrates the output format without making real API calls.
Run with: python tests/manual_test_compare.py
"""

import tempfile
from pathlib import Path
import yaml
from unittest.mock import patch
from typer.testing import CliRunner
from dakora.cli import app
from dakora.llm.models import ExecutionResult, ComparisonResult

runner = CliRunner()

def setup_test_project():
    """Create a temporary test project"""
    tmpdir = tempfile.mkdtemp()
    tmpdir = Path(tmpdir)
    prompts_dir = tmpdir / "prompts"
    prompts_dir.mkdir()

    test_template = {
        "id": "summarizer",
        "version": "1.0.0",
        "description": "Summarize text",
        "template": "Summarize: {{ input_text }}",
        "inputs": {
            "input_text": {
                "type": "string",
                "required": True
            }
        }
    }

    (prompts_dir / "summarizer.yaml").write_text(yaml.safe_dump(test_template))

    config = {
        "registry": "local",
        "prompt_dir": str(prompts_dir),
        "logging": {
            "enabled": False
        }
    }

    config_path = tmpdir / "dakora.yaml"
    config_path.write_text(yaml.safe_dump(config))

    return str(config_path)

def demo_table_output():
    """Demonstrate the default table output format"""
    print("\n" + "="*80)
    print("DEMO: Table Output (Default)")
    print("="*80 + "\n")

    config_path = setup_test_project()

    mock_results = [
        ExecutionResult(
            output="This article discusses the recent advances in artificial intelligence and machine learning technologies.",
            provider="openai",
            model="gpt-4",
            tokens_in=150,
            tokens_out=80,
            cost_usd=0.0045,
            latency_ms=1234
        ),
        ExecutionResult(
            output="The article explores cutting-edge developments in AI and ML, highlighting key breakthroughs and future implications.",
            provider="anthropic",
            model="claude-3-opus",
            tokens_in=150,
            tokens_out=75,
            cost_usd=0.0038,
            latency_ms=856
        ),
        ExecutionResult(
            output="A comprehensive overview of modern AI/ML advancements, their applications, and potential impact on various industries.",
            provider="google",
            model="gemini-pro",
            tokens_in=150,
            tokens_out=82,
            cost_usd=0.0012,
            latency_ms=2145
        )
    ]

    mock_comparison = ComparisonResult(
        results=mock_results,
        total_cost_usd=0.0095,
        total_tokens_in=450,
        total_tokens_out=237,
        successful_count=3,
        failed_count=0
    )

    with patch('dakora.vault.TemplateHandle.compare', return_value=mock_comparison):
        result = runner.invoke(app, [
            'compare',
            'summarizer',
            '--config', config_path,
            '--models', 'gpt-4,claude-3-opus,gemini-pro',
            '--input-text', 'This is a test article about artificial intelligence.'
        ])

    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    print(f"\nExit code: {result.exit_code}")


def demo_verbose_output():
    """Demonstrate the verbose output format"""
    print("\n" + "="*80)
    print("DEMO: Verbose Output")
    print("="*80 + "\n")

    config_path = setup_test_project()

    mock_results = [
        ExecutionResult(
            output="This article discusses the recent advances in artificial intelligence and machine learning technologies. Key points include neural networks, deep learning, and transformers.",
            provider="openai",
            model="gpt-4",
            tokens_in=150,
            tokens_out=80,
            cost_usd=0.0045,
            latency_ms=1234
        ),
        ExecutionResult(
            output="The article explores cutting-edge developments in AI and ML, highlighting key breakthroughs and future implications. It covers transformer architectures, large language models, and multimodal AI systems.",
            provider="anthropic",
            model="claude-3-opus",
            tokens_in=150,
            tokens_out=75,
            cost_usd=0.0038,
            latency_ms=856
        )
    ]

    mock_comparison = ComparisonResult(
        results=mock_results,
        total_cost_usd=0.0083,
        total_tokens_in=300,
        total_tokens_out=155,
        successful_count=2,
        failed_count=0
    )

    with patch('dakora.vault.TemplateHandle.compare', return_value=mock_comparison):
        result = runner.invoke(app, [
            'compare',
            'summarizer',
            '--config', config_path,
            '--models', 'gpt-4,claude-3-opus',
            '--input-text', 'This is a test article.',
            '--verbose'
        ])

    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    print(f"\nExit code: {result.exit_code}")


def demo_with_failure():
    """Demonstrate handling of partial failures"""
    print("\n" + "="*80)
    print("DEMO: Partial Failures")
    print("="*80 + "\n")

    config_path = setup_test_project()

    mock_results = [
        ExecutionResult(
            output="This article discusses recent AI advances.",
            provider="openai",
            model="gpt-4",
            tokens_in=150,
            tokens_out=80,
            cost_usd=0.0045,
            latency_ms=1234
        ),
        ExecutionResult(
            output="",
            provider="anthropic",
            model="claude-3-opus",
            tokens_in=0,
            tokens_out=0,
            cost_usd=0.0,
            latency_ms=0,
            error="API key not found"
        ),
        ExecutionResult(
            output="A comprehensive overview of AI/ML advancements.",
            provider="google",
            model="gemini-pro",
            tokens_in=150,
            tokens_out=82,
            cost_usd=0.0012,
            latency_ms=2145
        )
    ]

    mock_comparison = ComparisonResult(
        results=mock_results,
        total_cost_usd=0.0057,
        total_tokens_in=300,
        total_tokens_out=162,
        successful_count=2,
        failed_count=1
    )

    with patch('dakora.vault.TemplateHandle.compare', return_value=mock_comparison):
        result = runner.invoke(app, [
            'compare',
            'summarizer',
            '--config', config_path,
            '--models', 'gpt-4,claude-3-opus,gemini-pro',
            '--input-text', 'This is a test article.'
        ])

    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    print(f"\nExit code: {result.exit_code}")


def demo_json_output():
    """Demonstrate JSON output format"""
    print("\n" + "="*80)
    print("DEMO: JSON Output")
    print("="*80 + "\n")

    config_path = setup_test_project()

    mock_results = [
        ExecutionResult(
            output="AI article summary.",
            provider="openai",
            model="gpt-4",
            tokens_in=150,
            tokens_out=80,
            cost_usd=0.0045,
            latency_ms=1234
        ),
        ExecutionResult(
            output="ML advances overview.",
            provider="anthropic",
            model="claude-3-opus",
            tokens_in=150,
            tokens_out=75,
            cost_usd=0.0038,
            latency_ms=856
        )
    ]

    mock_comparison = ComparisonResult(
        results=mock_results,
        total_cost_usd=0.0083,
        total_tokens_in=300,
        total_tokens_out=155,
        successful_count=2,
        failed_count=0
    )

    with patch('dakora.vault.TemplateHandle.compare', return_value=mock_comparison):
        result = runner.invoke(app, [
            'compare',
            'summarizer',
            '--config', config_path,
            '--models', 'gpt-4,claude-3-opus',
            '--input-text', 'Test article.',
            '--json'
        ])

    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    print(f"\nExit code: {result.exit_code}")


if __name__ == "__main__":
    demo_table_output()
    demo_verbose_output()
    demo_with_failure()
    demo_json_output()

    print("\n" + "="*80)
    print("All demos completed successfully!")
    print("="*80 + "\n")
