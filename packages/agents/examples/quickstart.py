#!/usr/bin/env python3
"""
Dakora + MAF Quickstart Example

Shows how to use Dakora with Microsoft Agent Framework via OTEL integration.
"""

import asyncio
import os

from agent_framework.azure import AzureOpenAIChatClient
from dakora_client import Dakora
from dakora_agents.maf import DakoraIntegration


async def main():
    """Run a simple agent with Dakora tracking."""

    # 1. Initialize Dakora with API key
    dakora = Dakora(
        api_key=os.getenv("DAKORA_API_KEY", "dk_proj_..."),
        base_url=os.getenv("DAKORA_BASE_URL", "http://localhost:8000"),
    )

    # 2. Setup OTEL with Dakora integration (ONE LINE!)
    middleware = DakoraIntegration.setup(
        dakora,
        enable_sensitive_data=True,  # Capture messages in OTEL
        budget_check_cache_ttl=30,  # Cache budget checks for 30s
    )

    # 3. Create Azure OpenAI client with middleware
    azure_client = AzureOpenAIChatClient(
        endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        deployment_name=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        middleware=[middleware],  # Add Dakora middleware
    )

    # 4. Create an agent
    agent = azure_client.create_agent(
        id="quickstart-v1",
        name="QuickstartBot",
        instructions="You are a helpful assistant. Be concise.",
    )

    # 5. Run the agent - everything auto-tracked!
    print("Running agent...")
    response = await agent.run("What is 2+2?")

    print(f"\nAgent response: {response.messages[0].text}")
    print("\n✅ Execution automatically tracked in Dakora!")
    print("   - Budget checked (before execution)")
    print("   - Agent ID: quickstart-v1")
    print("   - Tokens tracked")
    print("   - Latency measured")
    print("   - Exported to Dakora API")

    # Optional: Force flush OTEL spans if you need immediate export
    # (useful for short-lived scripts, but not required for long-running apps)
    print("\nFlushing traces to Dakora...")
    DakoraIntegration.force_flush()
    await dakora.close()


async def example_with_templates():
    """Example using Dakora templates with auto-linking."""

    dakora = Dakora(
        api_key=os.getenv("DAKORA_API_KEY"),
        base_url=os.getenv("DAKORA_BASE_URL", "http://localhost:8000"),
    )

    # Setup OTEL integration
    middleware = DakoraIntegration.setup(dakora)

    azure_client = AzureOpenAIChatClient(
        endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        deployment_name=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        middleware=[middleware],
    )

    # Render a template from Dakora
    print("Rendering template...")
    greeting = await dakora.prompts.render(
        prompt_id="greeting",
        inputs={"name": "Alice"},
    )

    print(f"Rendered: {greeting.text}")

    # Create agent with template
    agent = azure_client.create_agent(
        id="template-bot-v1",
        name="TemplateBot",
        instructions=greeting.text,  # Use rendered template
    )

    # Run with template-linked message
    print("\nRunning agent with template...")
    user_message = await dakora.prompts.render(
        prompt_id="user_query",
        inputs={"question": "What's the weather?"},
    )

    response = await agent.run(user_message.to_message())

    print(f"\nAgent response: {response.messages[0].text}")
    print("\n✅ Template linkage captured!")
    print("   - greeting template (version X.X.X) used for instructions")
    print("   - user_query template (version X.X.X) used for message")
    print("   - Both linked to this execution in Dakora")

    # Force flush and cleanup
    DakoraIntegration.force_flush()
    await dakora.close()


async def example_with_jaeger():
    """Example sending traces to both Dakora AND Jaeger for local debugging."""

    dakora = Dakora(api_key=os.getenv("DAKORA_API_KEY"))

    # Setup with Jaeger integration (one line!)
    # Requires: docker run -d -p 16686:16686 -p 4317:4317 jaegertracing/all-in-one
    middleware = DakoraIntegration.setup_with_jaeger(
        dakora,
        jaeger_endpoint="http://localhost:4317",
    )

    azure_client = AzureOpenAIChatClient(
        endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        deployment_name=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        middleware=[middleware],
    )

    agent = azure_client.create_agent(
        id="jaeger-test-v1",
        name="JaegerTestBot",
        instructions="You are helpful.",
    )

    response = await agent.run("Hello!")

    print(f"\nAgent response: {response.messages[0].text}")
    print("\n✅ Traces sent to BOTH:")
    print("   - Dakora API (for analytics)")
    print("   - Jaeger (view at http://localhost:16686)")

    # Force flush and cleanup
    DakoraIntegration.force_flush()
    await dakora.close()


async def example_multi_agent():
    """Example with multiple agents - OTEL automatically creates span hierarchy."""

    dakora = Dakora(api_key=os.getenv("DAKORA_API_KEY"))
    middleware = DakoraIntegration.setup(dakora)

    azure_client = AzureOpenAIChatClient(
        endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        deployment_name=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        middleware=[middleware],
    )

    # Create two agents
    extractor = azure_client.create_agent(
        id="extractor-v1",
        name="EntityExtractor",
        instructions="Extract named entities from text. Return JSON.",
    )

    summarizer = azure_client.create_agent(
        id="summarizer-v1",
        name="Summarizer",
        instructions="Summarize text in one sentence.",
    )

    text = "Apple Inc. announced a new iPhone in Cupertino, California."

    # Run both agents - OTEL creates parent/child spans automatically!
    print("Running multi-agent pipeline...")

    entities_response = await extractor.run(f"Extract entities from: {text}")
    summary_response = await summarizer.run(f"Summarize: {text}")

    print(f"\nEntities: {entities_response.messages[0].text}")
    print(f"Summary: {summary_response.messages[0].text}")

    print("\n✅ Multi-agent execution tracked!")
    print("   - Both agents linked to same session")
    print("   - Parent/child relationship preserved")
    print("   - Total tokens = sum of both")

    # Force flush and cleanup
    DakoraIntegration.force_flush()
    await dakora.close()


if __name__ == "__main__":
    print("Dakora + MAF OTEL Integration Examples\n")
    print("=" * 50)

    # Run basic example
    print("\n1. Basic Example")
    print("-" * 50)
    asyncio.run(main())

    # Uncomment to run other examples:
    # print("\n2. Template Linkage Example")
    # print("-" * 50)
    # asyncio.run(example_with_templates())

    # print("\n3. Jaeger Integration Example")
    # print("-" * 50)
    # asyncio.run(example_with_jaeger())

    # print("\n4. Multi-Agent Example")
    # print("-" * 50)
    # asyncio.run(example_multi_agent())