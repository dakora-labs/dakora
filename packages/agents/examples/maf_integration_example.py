"""Examples for using Dakora MAF middleware to track agent executions."""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
import uuid
from collections import OrderedDict
from pathlib import Path
from typing import Awaitable, Callable, Sequence

from agent_framework import ChatAgent
from agent_framework.openai import OpenAIChatClient
from dakora_client import Dakora
from dakora_agents.maf import DakoraIntegration

DEFAULT_BASE_URL = "http://localhost:8000"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
EXAMPLE_DIR = Path(__file__).resolve().parent
EXAMPLE_ENV_FILE = EXAMPLE_DIR / ".env"


# Configure logging to see middleware debug output
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
    force=True,
)

logger = logging.getLogger(__name__)


def load_environment() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        logger.debug(
            "python-dotenv not installed; skipping .env loading for examples. "
            "Install with: uv pip install python-dotenv"
        )
        return

    if EXAMPLE_ENV_FILE.exists() and load_dotenv(EXAMPLE_ENV_FILE, override=False):
        logger.info("Loaded environment variables from %s", EXAMPLE_ENV_FILE)
    else:
        logger.debug("No .env file found at %s; skipping env load", EXAMPLE_ENV_FILE)


load_environment()
BASE_URL = os.getenv("DAKORA_BASE_URL", DEFAULT_BASE_URL)
OPENAI_MODEL = os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
DAKORA_API_KEY = os.getenv("DAKORA_API_KEY")

# Optionally suppress verbose libraries (keep only Dakora logs visible)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("opentelemetry").setLevel(logging.WARNING)

logger.info("Logging configured successfully")

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


def create_dakora_client() -> Dakora:
    return Dakora(base_url=BASE_URL, api_key=DAKORA_API_KEY)


async def setup_templates() -> None:
    """
    Create example templates in Dakora if they do not exist yet.

    In production you would manage templates through Dakora Studio or CI pipelines.
    """
    dakora = create_dakora_client()
    try:
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
    finally:
        await dakora.close()


async def simple_agent_example() -> None:
    """
    Example 1: single agent with Dakora tracking.

    Shows how to use Dakora templates for agent instructions with automatic observability.
    """
    dakora = create_dakora_client()
    middleware = DakoraIntegration.setup(dakora)

    try:
        instructions_result = await dakora.prompts.render("weather_agent_instructions", {})

        print("Using Dakora template: weather_agent_instructions")
        print(f"Template version: {instructions_result.version}")
        print(f"Instructions preview: {instructions_result.text[:100]}...")

        agent = ChatAgent(
            name="WeatherAgent",
            chat_client=OpenAIChatClient(model_id=OPENAI_MODEL),
            instructions=instructions_result.text,
            middleware=[middleware],
        )

        result = await agent.run("What's the weather like in Seattle?")
        print(f"\nAgent response: {result.messages[0].text}")
        print("\n* Execution metrics logged to Dakora via OTEL.")
    finally:
        DakoraIntegration.force_flush()
        await asyncio.sleep(0.5)
        await dakora.close()


async def template_tracking_example() -> None:
    """
    Example 2: template tracking in messages.

    Demonstrates tracking Dakora templates used in user messages.
    """
    dakora = create_dakora_client()
    middleware = DakoraIntegration.setup(dakora)

    try:
        instructions_result = await dakora.prompts.render("weather_agent_instructions", {})
        user_prompt_result = await dakora.prompts.render(
            "weather_query_template",
            {"city": "Seattle", "details": "temperature and conditions"},
        )

        print("Using Dakora templates:")
        print(f"  Instructions: weather_agent_instructions v{instructions_result.version}")
        print(f"  User prompt: weather_query_template v{user_prompt_result.version}")

        agent = ChatAgent(
            name="WeatherAgent",
            chat_client=OpenAIChatClient(model_id=OPENAI_MODEL),
            instructions=instructions_result.text,
            middleware=[middleware],
        )

        user_message = user_prompt_result.to_message()
        result = await agent.run(user_message)
        print(f"\nAgent response: {result.messages[0].text}")

        print("\n* Execution logged with template tracking.")
        print(f"  User message template: weather_query_template v{user_prompt_result.version}")
        print("  View in Dakora Studio -> Prompts -> weather_query_template -> Activity")
    finally:
        DakoraIntegration.force_flush()
        await asyncio.sleep(0.5)
        await dakora.close()


async def multi_agent_example() -> None:
    """
    Example 3: multi-agent workflow with session tracking.

    Demonstrates using a single middleware instance across multiple agents.
    OTEL automatically handles agent_id separation and parent/child relationships.
    """
    dakora = create_dakora_client()
    middleware = DakoraIntegration.setup(dakora)

    try:
        session_id = str(uuid.uuid4())
        print(f"Starting multi-agent workflow with session: {session_id}")

        researcher_instructions = await dakora.prompts.render("research_agent_instructions", {})
        researcher = ChatAgent(
            id="researcher",
            name="Researcher",
            chat_client=OpenAIChatClient(model_id=OPENAI_MODEL),
            instructions=researcher_instructions.text,
            middleware=[middleware],
        )

        writer_instructions = await dakora.prompts.render("writer_agent_instructions", {})
        writer = ChatAgent(
            id="writer",
            name="Writer",
            chat_client=OpenAIChatClient(model_id=OPENAI_MODEL),
            instructions=writer_instructions.text,
            middleware=[middleware],
        )

        print("\n1. Research phase...")
        research = await researcher.run("Research quantum computing basics")
        print(f"Research complete: {research.messages[0].text[:100]}...")

        print("\n2. Writing phase...")
        article = await writer.run(f"Write a brief article based on: {research.messages[0].text}")
        print(f"Article complete: {article.messages[0].text[:100]}...")

        print("\n* Multi-agent workflow complete.")
        print(f"  Session: {session_id}")
        print("  Both agents tracked separately by agent_id (via OTEL)")
        print("  Parent/child trace relationships handled automatically by OTEL")
    finally:
        DakoraIntegration.force_flush()
        await asyncio.sleep(0.5)
        await dakora.close()


async def conversation_tracking_example() -> None:
    """
    Example 4: multi-turn conversation tracking.

    Shows how OTEL automatically tracks multi-turn conversations.
    """
    dakora = create_dakora_client()
    middleware = DakoraIntegration.setup(dakora)

    try:
        conversation_id = f"conv-{uuid.uuid4()}"

        assistant_instructions = await dakora.prompts.render("assistant_instructions", {})

        agent = ChatAgent(
            name="Assistant",
            chat_client=OpenAIChatClient(model_id=OPENAI_MODEL),
            instructions=assistant_instructions.text,
            middleware=[middleware],
        )

        print(f"Starting conversation: {conversation_id}")

        result1 = await agent.run("Hi, what can you help me with?")
        print(f"Turn 1: {result1.messages[0].text}")

        result2 = await agent.run("Tell me about Python")
        print(f"Turn 2: {result2.messages[0].text}")

        print(f"\n* All turns logged under conversation: {conversation_id}")
        print("  View conversation history in Dakora Studio -> Traces")
    finally:
        DakoraIntegration.force_flush()
        await asyncio.sleep(0.5)
        await dakora.close()
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
    print(f"  Dakora API key: {_masked_api_key(DAKORA_API_KEY)}")
    print(f"  OpenAI model: {OPENAI_MODEL}")
    print("\nUse --list to see available examples or --example to run specific ones.\n")

    print("Setting up example templates...")
    await setup_templates()
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
