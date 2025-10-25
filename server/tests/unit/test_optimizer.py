"""Unit tests for the optimizer module."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from dakora_server.core.optimizer import OptimizationEngine, OptimizationRequest
from dakora_server.core.optimizer.types import Variant, Insight
from dakora_server.core.llm.provider import ExecutionResult


class MockLLMProvider:
    """Mock LLM provider for testing."""

    async def execute(self, prompt: str, model: str, **kwargs) -> ExecutionResult:
        """Mock execute that returns canned responses."""
        # Return different responses based on prompt content
        if "clarity" in prompt.lower():
            content = "Make this clearer:\n{{ name }}\nImproved template with better clarity."
        elif "specificity" in prompt.lower():
            content = "Make this specific:\n{{ name }}\nImproved template with more specific constraints."
        elif "efficiency" in prompt.lower():
            content = "Make this efficient:\n{{ name }}\nImproved template, more concise."
        elif "test cases" in prompt.lower():
            content = '''[
                {"inputs": {"name": "Test"}, "purpose": "Basic test"},
                {"inputs": {"name": ""}, "purpose": "Edge case - empty"}
            ]'''
        elif "evaluate" in prompt.lower() or "critic" in prompt.lower():
            content = '''{
                "score": 8.5,
                "insights": [
                    {
                        "category": "clarity",
                        "description": "Improved structure",
                        "impact": "Reduces ambiguity by 30%"
                    }
                ]
            }'''
        elif "explaining" in prompt.lower() or "improvements" in prompt.lower():
            content = '''{
                "insights": [
                    {
                        "category": "clarity",
                        "description": "Better formatting",
                        "impact": "Easier to understand"
                    }
                ]
            }'''
        else:
            content = "Optimized template content"

        return ExecutionResult(
            content=content,
            tokens_input=100,
            tokens_output=50,
            tokens_total=150,
            cost_usd=0.001,
            latency_ms=500,
            model=model,
            provider="mock",
        )

    def get_available_models(self):
        """Mock available models."""
        return []


@pytest.mark.asyncio
async def test_optimization_engine_basic():
    """Test that optimization engine runs end-to-end."""
    provider = MockLLMProvider()
    engine = OptimizationEngine(provider, model="gpt-4o-mini")

    request = OptimizationRequest(
        template="Hello {{ name }}! How are you?",
        test_cases=None,  # Will generate synthetic
    )

    result = await engine.optimize(request)

    # Check that we got a result
    assert result is not None
    assert result.original_template == request.template
    assert result.best_variant is not None
    assert len(result.all_variants) == 3
    assert result.best_variant.strategy in ["clarity", "specificity", "efficiency"]


@pytest.mark.asyncio
async def test_optimization_with_test_cases():
    """Test optimization with provided test cases."""
    provider = MockLLMProvider()
    engine = OptimizationEngine(provider, model="gpt-4o-mini")

    test_cases = [
        {"inputs": {"name": "Alice"}, "purpose": "Normal case"},
        {"inputs": {"name": ""}, "purpose": "Empty name"},
    ]

    request = OptimizationRequest(
        template="Greet {{ name }}",
        test_cases=test_cases,
    )

    result = await engine.optimize(request)

    assert result is not None
    assert len(result.all_variants) == 3


@pytest.mark.asyncio
async def test_variant_generator():
    """Test variant generator creates 3 variants."""
    from dakora_server.core.optimizer.generator import VariantGenerator

    provider = MockLLMProvider()
    generator = VariantGenerator(provider, model="gpt-4o-mini")

    variants = await generator.generate_variants("Hello {{ name }}")

    assert len(variants) == 3
    assert variants[0].strategy == "clarity"
    assert variants[1].strategy == "specificity"
    assert variants[2].strategy == "efficiency"
    assert all(v.template for v in variants)
    assert all(v.token_count is not None for v in variants)


@pytest.mark.asyncio
async def test_variant_evaluator():
    """Test variant evaluator scores variants."""
    from dakora_server.core.optimizer.evaluator import VariantEvaluator

    provider = MockLLMProvider()
    evaluator = VariantEvaluator(provider, model="gpt-4o-mini")

    variant = Variant(
        template="Optimized {{ name }}",
        strategy="clarity",
        token_count=20,
    )

    score = await evaluator.evaluate_variant(
        original_template="Hello {{ name }}",
        variant=variant,
        test_cases=None,
    )

    assert score is not None
    assert score.variant == variant
    assert 0 <= score.score <= 10