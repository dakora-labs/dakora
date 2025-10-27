"""Examples for using Dakora MAF middleware to track agent executions."""

from __future__ import annotations

import argparse
import asyncio
import sys
import uuid
from collections import OrderedDict
from typing import Awaitable, Callable, Iterable, Sequence

from agent_framework import ChatAgent
from agent_framework.openai import OpenAIChatClient
from dakora_client import Dakora
from dakora_agents.maf import create_dakora_middleware

BASE_URL = "http://localhost:8000"  # Your Dakora server URL
PROJECT_ID = "73996404-48e2-4e53-bd6d-ce9e30b4f887"  # Your Dakora project ID
API_KEY = "dk_your_api_key"  # Your Dakora API key

# OpenAI configuration (set OPENAI_API_KEY or Azure OpenAI env vars before running)
OPENAI_MODEL = "gpt-4o-mini"

TEMPLATES = {
    "weather_agent_instructions": {
        "id": "weather_agent_instructions",
        "version": "1.0.0",
        "description": "System instructions for a weather information agent",
        "template": (
            "You are a helpful weather assistant. Provide accurate weather information and forecasts.\n"
            "When users ask about weather, be concise but informative."
        ),
        "inputs": {},
        "metadata": {"category": "agent-instructions", "framework": "maf"},
    },
    "research_agent_instructions": {
        "id": "research_agent_instructions",
        "version": "1.0.0",
        "description": "Instructions for a research agent",
        "template": "You are a thorough research agent. Gather comprehensive information and organize findings clearly.",
        "inputs": {},
        "metadata": {"category": "agent-instructions"},
    },
    "writer_agent_instructions": {
        "id": "writer_agent_instructions",
        "version": "1.0.0",
        "description": "Instructions for a writer agent",
        "template": "You are a skilled content writer. Transform research into clear, engaging content.",
        "inputs": {},
        "metadata": {"category": "agent-instructions"},
    },
    "assistant_instructions": {
        "id": "assistant_instructions",
        "version": "1.0.0",
        "description": "General assistant instructions",
        "template": "You are a helpful AI assistant. Provide accurate, friendly, and relevant responses.",
        "inputs": {},
        "metadata": {"category": "agent-instructions"},
    },
    "weather_query_template": {
        "id": "weather_query_template",
        "version": "1.0.0",
        "description": "Template for weather queries with parameters",
        "template": "I need weather information for {{city}}. Please provide {{details}}.",
        "inputs": {
            "city": {"type": "string", "required": True},
            "details": {"type": "string", "required": True, "default": "current conditions"},
        },
        "metadata": {"category": "user-prompts"},
    },
}

ExampleHandler = Callable[[], Awaitable[None]]


def _masked_api_key(api_key: str | None) -> str:
    if not api_key:
        return "None"
    return f"***{api_key[-4:]}"


async def setup_templates(base_url: str, project_id: str, api_key: str | None = None) -> None:
    """
    Create example templates in Dakora if they do not exist yet.

    In production you would manage templates through Dakora Studio or CI pipelines.
    """
    dakora = Dakora(base_url=base_url, api_key=api_key, project_id=project_id)

    for template_id, template_data in TEMPLATES.items():
        try:
            try:
                await dakora.prompts.get(template_id)
                print(f"* Template '{template_id}' already exists")
                continue
            except Exception:
                pass

            await dakora.prompts.create(
                prompt_id=template_data["id"],
                version=template_data["version"],
                description=template_data.get("description"),
                template=template_data["template"],
                inputs=template_data.get("inputs", {}),
                metadata=template_data.get("metadata", {}),
            )
            print(f"* Created template '{template_id}'")
        except Exception as exc:
            print(f"! Error setting up '{template_id}': {exc}")


async def simple_agent_example() -> None:
    """
    Example 1: single agent with Dakora tracking.

    Shows how to use Dakora templates for agent instructions with automatic observability.
    """
    dakora = Dakora(base_url=BASE_URL, api_key=API_KEY, project_id=PROJECT_ID)
    instructions_result = await dakora.prompts.render("weather_agent_instructions", {})

    print("Using Dakora template: weather_agent_instructions")
    print(f"Template version: {instructions_result.version}")
    print(f"Instructions preview: {instructions_result.text[:100]}...")

    middleware = create_dakora_middleware(
        dakora_client=dakora,
        instruction=instructions_result,
    )

    agent = ChatAgent(
        name="WeatherAgent",
        chat_client=OpenAIChatClient(model_id=OPENAI_MODEL),
        instructions=instructions_result.text,
        metadata={"dakora_agent_id": "weather_agent"},
        middleware=[middleware],
    )

    result = await agent.run("What's the weather like in Seattle?")
    print(f"\nAgent response: {result}")
    print("\n* Execution metrics logged to Dakora.")
    print(f"  View in Dakora Studio -> Projects -> {PROJECT_ID} -> Traces")

    await asyncio.sleep(0.5)


async def template_tracking_example() -> None:
    """
    Example 2: template tracking in messages.

    Demonstrates tracking Dakora templates used in user messages.
    """
    dakora = Dakora(base_url=BASE_URL, api_key=API_KEY, project_id=PROJECT_ID)
    instructions_result = await dakora.prompts.render("weather_agent_instructions", {})
    user_prompt_result = await dakora.prompts.render(
        "weather_query_template",
        {"city": "Seattle", "details": "temperature and conditions"},
    )

    print("Using Dakora templates:")
    print(f"  Instructions: weather_agent_instructions v{instructions_result.version}")
    print(f"  User prompt: weather_query_template v{user_prompt_result.version}")

    middleware = create_dakora_middleware(
        dakora_client=dakora,
        instruction=instructions_result,
    )

    agent = ChatAgent(
        name="WeatherAgent",
        chat_client=OpenAIChatClient(model_id=OPENAI_MODEL),
        instructions=instructions_result.text,
        metadata={"dakora_agent_id": "weather_agent"},
        middleware=[middleware],
    )

    user_message = user_prompt_result.to_message()
    result = await agent.run(user_message)
    print(f"\nAgent response: {result}")

    print("\n* Execution logged with template tracking.")
    print(f"  User message template: weather_query_template v{user_prompt_result.version}")
    print("  View in Dakora Studio -> Prompts -> weather_query_template -> Activity")

    await asyncio.sleep(0.5)


async def multi_agent_example() -> None:
    """
    Example 3: multi-agent workflow with session tracking.

    Illustrates linking multiple agents under a single session.
    """
    dakora = Dakora(base_url=BASE_URL, api_key=API_KEY, project_id=PROJECT_ID)
    session_id = str(uuid.uuid4())

    print(f"Starting multi-agent workflow with session: {session_id}")

    researcher_instructions = await dakora.prompts.render("research_agent_instructions", {})
    researcher_middleware = create_dakora_middleware(
        dakora_client=dakora,
        session_id=session_id,
        instruction=researcher_instructions,
    )
    researcher = ChatAgent(
        name="Researcher",
        chat_client=OpenAIChatClient(model_id=OPENAI_MODEL),
        instructions=researcher_instructions.text,
        metadata={"dakora_agent_id": "researcher"},
        middleware=[researcher_middleware],
    )

    writer_instructions = await dakora.prompts.render("writer_agent_instructions", {})
    writer_middleware = create_dakora_middleware(
        dakora_client=dakora,
        session_id=session_id,
        instruction=writer_instructions,
    )
    writer = ChatAgent(
        name="Writer",
        chat_client=OpenAIChatClient(model_id=OPENAI_MODEL),
        instructions=writer_instructions.text,
        metadata={"dakora_agent_id": "writer"},
        middleware=[writer_middleware],
    )

    print("\n1. Research phase...")
    research = await researcher.run("Research quantum computing basics")
    print(f"Research complete: {str(research)[:100]}...")

    research_trace_id = researcher_middleware.last_trace_id
    if research_trace_id:
        writer_middleware.set_parent_trace_id(research_trace_id)
        print(f"  Linked writer trace to parent trace: {research_trace_id}")

    print("\n2. Writing phase...")
    article = await writer.run(f"Write a brief article based on: {research}")
    print(f"Article complete: {str(article)[:100]}...")
    if writer_middleware.last_trace_id:
        print(f"  Writer trace: {writer_middleware.last_trace_id} (parent: {research_trace_id})")

    print("\n* Multi-agent workflow complete.")
    print(f"  Session: {session_id}")
    print("  Both agents tracked separately with their own agent_id")
    print("  Parent/child trace link available in Dakora Studio")

    await asyncio.sleep(0.5)


async def conversation_tracking_example() -> None:
    """
    Example 4: multi-turn conversation tracking.

    Shows how to reuse a session identifier across multiple agent turns.
    """
    dakora = Dakora(base_url=BASE_URL, api_key=API_KEY, project_id=PROJECT_ID)
    conversation_id = f"conv-{uuid.uuid4()}"

    assistant_instructions = await dakora.prompts.render("assistant_instructions", {})

    middleware = create_dakora_middleware(
        dakora_client=dakora,
        session_id=conversation_id,
        instruction=assistant_instructions,
    )

    agent = ChatAgent(
        name="Assistant",
        chat_client=OpenAIChatClient(model_id=OPENAI_MODEL),
        instructions=assistant_instructions.text,
        metadata={"dakora_agent_id": "assistant"},
        middleware=[middleware],
    )

    print(f"Starting conversation: {conversation_id}")

    result1 = await agent.run("Hi, what can you help me with?")
    print(f"Turn 1: {result1}")

    result2 = await agent.run("Tell me about Python")
    print(f"Turn 2: {result2}")

    print(f"\n* All turns logged under conversation: {conversation_id}")
    print("  View conversation history in Dakora Studio -> Sessions")

    await asyncio.sleep(0.5)


EXAMPLES: OrderedDict[str, tuple[str, ExampleHandler]] = OrderedDict(
    [
        ("simple", ("Simple Agent", simple_agent_example)),
        ("template-tracking", ("Template Tracking", template_tracking_example)),
        ("multi-agent", ("Multi-Agent Workflow", multi_agent_example)),
        ("conversation", ("Conversation Tracking", conversation_tracking_example)),
    ]
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Dakora MAF middleware integration examples.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available examples and exit.",
    )
    parser.add_argument(
        "-e",
        "--example",
        dest="examples",
        action="append",
        choices=list(EXAMPLES.keys()),
        help="Example(s) to run (can be provided multiple times). Defaults to all.",
    )
    return parser.parse_args()


async def run_examples(example_names: Sequence[str]) -> None:
    for name in example_names:
        title, handler = EXAMPLES[name]
        print(f"\n--- Example: {title} ---")
        await handler()


async def main(example_names: Sequence[str]) -> None:
    print("=== Dakora MAF Middleware Examples ===\n")
    print("Configuration:")
    print(f"  Server: {BASE_URL}")
    print(f"  Project: {PROJECT_ID}")
    print(f"  API Key: {_masked_api_key(API_KEY)}")
    print("\nUse --list to see available examples or --example to run specific ones.\n")

    print("Setting up example templates...")
    await setup_templates(BASE_URL, PROJECT_ID, API_KEY)
    print("Templates ready.\n")

    await run_examples(example_names)


if __name__ == "__main__":
    arguments = parse_args()
    if arguments.list:
        print("Available examples:")
        for key, (title, _) in EXAMPLES.items():
            print(f"  {key:20} - {title}")
        sys.exit(0)

    selected_examples: Sequence[str]
    if arguments.examples:
        selected_examples = arguments.examples
    else:
        selected_examples = list(EXAMPLES.keys())

    asyncio.run(main(selected_examples))
