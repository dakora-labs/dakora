"""
Demo script for the prompt optimization engine.

This shows how to use the OptimizationEngine with a real LLM provider.

Usage:
    export AZURE_OPENAI_ENDPOINT="https://YOUR_INSTANCE.openai.azure.com"
    export AZURE_OPENAI_API_KEY="your-api-key"
    export AZURE_OPENAI_DEPLOYMENT="gpt-4o-mini"

    python server/examples/optimizer_demo.py
"""

import asyncio
import os
from dakora_server.core.optimizer import OptimizationEngine, OptimizationRequest
from dakora_server.core.llm import AzureOpenAIProvider


async def main():
    """Run optimization demo."""
    # Get credentials from environment
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")

    if not endpoint or not api_key:
        print("ERROR: Set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY")
        return

    print(f"Using Azure OpenAI: {endpoint}")
    print(f"Deployment: {deployment}\n")

    # Create provider
    provider = AzureOpenAIProvider(
        endpoint=endpoint,
        api_key=api_key,
        deployment_name=deployment,
    )

    # Create optimization engine
    engine = OptimizationEngine(provider, model=deployment)

    # Example template to optimize
    original_template = """Write a summary of this text.

Text: {{ text }}

Summary:"""

    print("Original template:")
    print("-" * 60)
    print(original_template)
    print("-" * 60)
    print()

    # Create optimization request
    request = OptimizationRequest(
        template=original_template,
        test_cases=[
            {
                "inputs": {"text": "This is a short text about AI."},
                "purpose": "Normal case",
            },
            {
                "inputs": {"text": ""},
                "purpose": "Edge case - empty text",
            },
        ],
    )

    print("Running optimization... (this may take 30-60 seconds)")
    print()

    # Run optimization
    result = await engine.optimize(request)

    # Display results
    print("✨ OPTIMIZATION COMPLETE!")
    print("=" * 60)
    print()

    print("Best variant (strategy: {})".format(result.best_variant.strategy))
    print("-" * 60)
    print(result.best_variant.template)
    print("-" * 60)
    print()

    if result.token_reduction_pct is not None:
        print(f"Token reduction: {result.token_reduction_pct:.1f}%")
        print()

    print("Key improvements:")
    for i, insight in enumerate(result.insights, 1):
        print(f"{i}. [{insight.category}] {insight.description}")
        print(f"   Impact: {insight.impact}")
        print()

    print("All variants generated:")
    for i, variant in enumerate(result.all_variants, 1):
        print(f"\n{i}. {variant.strategy.upper()} ({variant.token_count} tokens)")
        print("-" * 40)
        print(variant.template[:100] + "..." if len(variant.template) > 100 else variant.template)


if __name__ == "__main__":
    asyncio.run(main())