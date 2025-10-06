import pytest
from pydantic import ValidationError
from dakora.llm.models import ExecutionResult

def test_execution_result_valid():
    result = ExecutionResult(
        output="Test response",
        provider="openai",
        model="gpt-5",
        tokens_in=100,
        tokens_out=50,
        cost_usd=0.05,
        latency_ms=1200
    )
    assert result.output == "Test response"
    assert result.provider == "openai"
    assert result.model == "gpt-5"
    assert result.tokens_in == 100
    assert result.tokens_out == 50
    assert result.cost_usd == 0.05
    assert result.latency_ms == 1200

def test_execution_result_validation_negative_tokens():
    with pytest.raises(ValidationError):
        ExecutionResult(
            output="Test",
            provider="openai",
            model="gpt-5",
            tokens_in=-1,
            tokens_out=50,
            cost_usd=0.05,
            latency_ms=1200
        )

def test_execution_result_validation_negative_cost():
    with pytest.raises(ValidationError):
        ExecutionResult(
            output="Test",
            provider="openai",
            model="gpt-5",
            tokens_in=100,
            tokens_out=50,
            cost_usd=-0.05,
            latency_ms=1200
        )

def test_execution_result_validation_negative_latency():
    with pytest.raises(ValidationError):
        ExecutionResult(
            output="Test",
            provider="openai",
            model="gpt-5",
            tokens_in=100,
            tokens_out=50,
            cost_usd=0.05,
            latency_ms=-1
        )

def test_execution_result_zero_values():
    result = ExecutionResult(
        output="",
        provider="anthropic",
        model="claude-3-opus",
        tokens_in=0,
        tokens_out=0,
        cost_usd=0.0,
        latency_ms=0
    )
    assert result.tokens_in == 0
    assert result.tokens_out == 0
    assert result.cost_usd == 0.0
    assert result.latency_ms == 0