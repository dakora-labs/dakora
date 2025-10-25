"""Prompt optimization engine for Dakora.

This module provides intelligent prompt optimization using LLM-powered
variant generation and evaluation.

Example usage:
    from dakora_server.core.optimizer import OptimizationEngine
    from dakora_server.core.optimizer.types import OptimizationRequest
    from dakora_server.core.llm import AzureOpenAIProvider

    # Create LLM provider
    provider = AzureOpenAIProvider(
        endpoint="https://YOUR_INSTANCE.openai.azure.com",
        api_key="YOUR_API_KEY",
        deployment_name="gpt-4o-mini",
    )

    # Create engine
    engine = OptimizationEngine(provider, model="gpt-4o-mini")

    # Optimize a prompt
    request = OptimizationRequest(
        template="Hello {{ name }}!",
        test_cases=[{"inputs": {"name": "World"}}],
    )
    result = await engine.optimize(request)

    print(result.best_variant.template)
    print(result.insights)
"""

from .engine import OptimizationEngine
from .quota import OptimizationQuotaService, OptimizationQuotaUsage, OPTIMIZATION_QUOTA_TIERS
from .types import (
    Insight,
    OptimizationRequest,
    OptimizationResult,
    Variant,
    VariantScore,
)

__all__ = [
    # Main engine
    "OptimizationEngine",
    # Quota management
    "OptimizationQuotaService",
    "OptimizationQuotaUsage",
    "OPTIMIZATION_QUOTA_TIERS",
    # Types
    "Insight",
    "OptimizationRequest",
    "OptimizationResult",
    "Variant",
    "VariantScore",
]