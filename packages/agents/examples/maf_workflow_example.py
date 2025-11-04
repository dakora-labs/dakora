"""Dakora + MAF Workflow Example - Content Review with Quality Routing.

This sample demonstrates:
- Using MAF WorkflowBuilder with Dakora tracking
- Multiple agents in a workflow with conditional routing
- Template-based agent instructions
- Quality-based workflow paths with convergence

Use case: Content creation with automated review.
Writer creates content, Reviewer evaluates quality:
  - High quality (score >= 80): → Publisher → Summarizer
  - Low quality (score < 80): → Editor → Publisher → Summarizer
Both paths converge at Summarizer for final report.

All agent executions are tracked in Dakora via OTEL.
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Any

from agent_framework import AgentExecutorResponse, WorkflowBuilder
from agent_framework.openai import OpenAIChatClient
from dakora_client import Dakora
from dakora_agents.maf import DakoraIntegration
from pydantic import BaseModel

DEFAULT_BASE_URL = "http://localhost:8000"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
EXAMPLE_DIR = Path(__file__).resolve().parent
EXAMPLE_ENV_FILE = EXAMPLE_DIR / ".env"

# Configure logging to see workflow execution
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
    force=True,
)

logger = logging.getLogger(__name__)

# Suppress verbose libraries
logging.getLogger("httpx").setLevel(logging.ERROR)
logging.getLogger("httpcore").setLevel(logging.ERROR)
logging.getLogger("opentelemetry").setLevel(logging.ERROR)


def load_environment() -> None:
    """Load environment variables from .env file if available."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        logger.debug("python-dotenv not installed; skipping .env loading")
        return

    if EXAMPLE_ENV_FILE.exists() and load_dotenv(EXAMPLE_ENV_FILE, override=False):
        logger.info("Loaded environment variables from %s", EXAMPLE_ENV_FILE)
    else:
        logger.debug("No .env file found at %s", EXAMPLE_ENV_FILE)


load_environment()
BASE_URL = os.getenv("DAKORA_BASE_URL", DEFAULT_BASE_URL)
OPENAI_MODEL = os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
DAKORA_API_KEY = os.getenv("DAKORA_API_KEY")


# Define structured output for review results
class ReviewResult(BaseModel):
    """Review evaluation with scores and feedback."""

    score: int  # Overall quality score (0-100)
    feedback: str  # Concise, actionable feedback
    clarity: int  # Clarity score (0-100)
    completeness: int  # Completeness score (0-100)
    accuracy: int  # Accuracy score (0-100)
    structure: int  # Structure score (0-100)


# Workflow template definitions for Dakora
WORKFLOW_TEMPLATES = {
    "writer_instructions": {
        "id": "writer_instructions",
        "version": "1.0.0",
        "description": "Instructions for content writer agent in workflow",
        "template": (
            "You are an excellent content writer specializing in {{content_type}}. "
            "Create clear, engaging content based on the user's request. "
            "Focus on clarity, accuracy, and proper structure. "
            "Tone: {{tone}}."
        ),
        "inputs": {
            "content_type": {"type": "string", "required": False, "default": "technical articles"},
            "tone": {"type": "string", "required": False, "default": "professional"},
        },
        "metadata": {"category": "workflow-agent-instructions", "framework": "maf"},
    },
    "reviewer_instructions": {
        "id": "reviewer_instructions",
        "version": "1.0.0",
        "description": "Instructions for content reviewer agent in workflow",
        "template": (
            "You are an expert content reviewer specializing in {{specialty}}. "
            "Evaluate the writer's content based on:\n"
            "1. Clarity - Is it easy to understand?\n"
            "2. Completeness - Does it fully address the topic?\n"
            "3. Accuracy - Is the information correct?\n"
            "4. Structure - Is it well-organized?\n\n"
            "Return a JSON object with:\n"
            "- score: overall quality (0-100)\n"
            "- feedback: concise, actionable feedback\n"
            "- clarity, completeness, accuracy, structure: individual scores (0-100)"
        ),
        "inputs": {
            "specialty": {"type": "string", "required": False, "default": "general content"},
        },
        "metadata": {"category": "workflow-agent-instructions", "framework": "maf"},
    },
    "editor_instructions": {
        "id": "editor_instructions",
        "version": "1.0.0",
        "description": "Instructions for editor agent in workflow",
        "template": (
            "You are a skilled editor with expertise in {{expertise_area}}. "
            "You will receive content along with review feedback. "
            "Improve the content by addressing all the issues mentioned in the feedback. "
            "Maintain the original intent while enhancing clarity, completeness, accuracy, and structure."
        ),
        "inputs": {
            "expertise_area": {"type": "string", "required": False, "default": "technical writing"},
        },
        "metadata": {"category": "workflow-agent-instructions", "framework": "maf"},
    },
    "publisher_instructions": {
        "id": "publisher_instructions",
        "version": "1.0.0",
        "description": "Instructions for publisher agent in workflow",
        "template": (
            "You are a publishing agent specializing in {{publication_type}}. "
            "You receive either approved content or edited content. "
            "Format it for publication with proper headings, structure, and {{format_style}} formatting."
        ),
        "inputs": {
            "publication_type": {"type": "string", "required": False, "default": "blog posts"},
            "format_style": {"type": "string", "required": False, "default": "markdown"},
        },
        "metadata": {"category": "workflow-agent-instructions", "framework": "maf"},
    },
    "summarizer_instructions": {
        "id": "summarizer_instructions",
        "version": "1.0.0",
        "description": "Instructions for summarizer agent in workflow",
        "template": (
            "You are a summarizer agent. "
            "Create a final publication report that includes:\n"
            "1. A brief summary of the published content\n"
            "2. The workflow path taken (direct approval or edited)\n"
            "3. Key highlights and takeaways\n"
            "Keep it concise and {{style}}."
        ),
        "inputs": {
            "style": {"type": "string", "required": False, "default": "professional"},
        },
        "metadata": {"category": "workflow-agent-instructions", "framework": "maf"},
    },
}


# Condition functions for workflow routing
def needs_editing(message: Any) -> bool:
    """Check if content needs editing based on review score."""
    if not isinstance(message, AgentExecutorResponse):
        return False
    try:
        review = ReviewResult.model_validate_json(message.agent_run_response.text)
        return review.score < 80
    except Exception:
        return False


def is_approved(message: Any) -> bool:
    """Check if content is approved (high quality)."""
    if not isinstance(message, AgentExecutorResponse):
        return True
    try:
        review = ReviewResult.model_validate_json(message.agent_run_response.text)
        return review.score >= 80
    except Exception:
        return True


async def setup_workflow_templates(dakora: Dakora) -> None:
    """
    Create workflow templates in Dakora if they do not exist yet.

    In production you would manage templates through Dakora Studio or CI pipelines.
    """
    try:
        for template_id, template_data in WORKFLOW_TEMPLATES.items():
            try:
                try:
                    await dakora.prompts.get(template_id)
                    logger.info(f"Template '{template_id}' already exists")
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
                logger.info(f"Created template '{template_id}'")
            except Exception as exc:
                logger.error(f"Error setting up '{template_id}': {exc}")
    except Exception as e:
        logger.error(f"Error in setup_workflow_templates: {e}")


async def build_workflow_with_dakora() -> WorkflowBuilder:
    """
    Build the content review workflow with Dakora-tracked agents.

    All agents use templates from Dakora and are instrumented with
    DakoraIntegration middleware for automatic observability.
    """
    dakora = Dakora(base_url=BASE_URL, api_key=DAKORA_API_KEY)
    middleware = DakoraIntegration.setup(dakora)

    try:
        # Render agent instructions from Dakora templates
        writer_instructions = await dakora.prompts.render(
            "writer_instructions",
            {"content_type": "technical blog posts", "tone": "engaging and informative"}
        )
        
        reviewer_instructions = await dakora.prompts.render(
            "reviewer_instructions",
            {"specialty": "technical content"}
        )
        
        editor_instructions = await dakora.prompts.render(
            "editor_instructions",
            {"expertise_area": "technical writing and documentation"}
        )
        
        publisher_instructions = await dakora.prompts.render(
            "publisher_instructions",
            {"publication_type": "blog posts", "format_style": "markdown"}
        )
        
        summarizer_instructions = await dakora.prompts.render(
            "summarizer_instructions",
            {"style": "professional and concise"}
        )

        logger.info("Using Dakora templates for all workflow agents:")
        logger.info(f"  Writer: writer_instructions v{writer_instructions.version}")
        logger.info(f"  Reviewer: reviewer_instructions v{reviewer_instructions.version}")
        logger.info(f"  Editor: editor_instructions v{editor_instructions.version}")
        logger.info(f"  Publisher: publisher_instructions v{publisher_instructions.version}")
        logger.info(f"  Summarizer: summarizer_instructions v{summarizer_instructions.version}")

        # Create OpenAI chat client
        chat_client = OpenAIChatClient(model_id=OPENAI_MODEL)

        # Create Writer agent with Dakora tracking
        writer = chat_client.create_agent(
            id="writer",
            name="Writer",
            instructions=writer_instructions.text,
            middleware=[middleware],
        )

        # Create Reviewer agent with structured output and Dakora tracking
        reviewer = chat_client.create_agent(
            id="reviewer",
            name="Reviewer",
            instructions=reviewer_instructions.text,
            response_format=ReviewResult,
            middleware=[middleware],
        )

        # Create Editor agent with Dakora tracking
        editor = chat_client.create_agent(
            id="editor",
            name="Editor",
            instructions=editor_instructions.text,
            middleware=[middleware],
        )

        # Create Publisher agent with Dakora tracking
        publisher = chat_client.create_agent(
            id="publisher",
            name="Publisher",
            instructions=publisher_instructions.text,
            middleware=[middleware],
        )

        # Create Summarizer agent with Dakora tracking
        summarizer = chat_client.create_agent(
            id="summarizer",
            name="Summarizer",
            instructions=summarizer_instructions.text,
            middleware=[middleware],
        )

        # Build workflow with branching and convergence:
        # Writer → Reviewer → [branches]:
        #   - If score >= 80: → Publisher → Summarizer (direct approval path)
        #   - If score < 80: → Editor → Publisher → Summarizer (improvement path)
        # Both paths converge at Summarizer for final report
        workflow = (
            WorkflowBuilder(
                name="Dakora Content Review Workflow",
                description="Multi-agent content creation workflow with Dakora tracking and quality-based routing",
            )
            .set_start_executor(writer)
            .add_edge(writer, reviewer)
            # Branch 1: High quality (>= 80) goes directly to publisher
            .add_edge(reviewer, publisher, condition=is_approved)
            # Branch 2: Low quality (< 80) goes to editor first, then publisher
            .add_edge(reviewer, editor, condition=needs_editing)
            .add_edge(editor, publisher)
            # Both paths converge: Publisher → Summarizer
            .add_edge(publisher, summarizer)
            .build()
        )

        logger.info("Workflow built successfully with Dakora-tracked agents")
        return workflow

    except Exception as e:
        logger.error(f"Error building workflow: {e}")
        raise
    finally:
        # Note: We keep the dakora client alive since middleware needs it
        pass


async def run_workflow_example() -> None:
    """
    Run the content review workflow with Dakora tracking.

    This demonstrates a complete multi-agent workflow where:
    1. All agents use Dakora templates for instructions
    2. All executions are automatically tracked via OTEL
    3. Workflow routing is based on structured review scores
    4. All data can be viewed in Dakora Studio
    """
    dakora = Dakora(base_url=BASE_URL, api_key=DAKORA_API_KEY)

    try:
        logger.info("=== Dakora + MAF Workflow Example ===\n")
        logger.info("Configuration:")
        logger.info(f"  Dakora Server: {BASE_URL}")
        logger.info(f"  OpenAI Model: {OPENAI_MODEL}\n")

        # Setup templates
        logger.info("Setting up workflow templates in Dakora...")
        await setup_workflow_templates(dakora)
        logger.info("Templates ready.\n")

        # Build workflow with Dakora tracking
        logger.info("Building workflow with Dakora-tracked agents...")
        workflow = await build_workflow_with_dakora()
        logger.info("Workflow ready.\n")

        # Run the workflow
        logger.info("Starting workflow execution...")
        logger.info("Task: Write a brief article about the benefits of async programming in Python\n")

        result = await workflow.run("Write a brief article about the benefits of async programming in Python")

        logger.info("\n=== Workflow Complete ===")
        # Get the final outputs from the workflow result
        outputs = result.get_outputs()
        final_output = outputs[-1] if outputs else "No output"
        logger.info(f"Final output:\n{final_output}\n")

        logger.info("All agent executions tracked in Dakora!")
        logger.info("View in Dakora Studio:")
        logger.info("  - Traces: See the complete workflow execution path")
        logger.info("  - Prompts: View template usage and versions")
        logger.info("  - Executions: Detailed metrics for each agent")

    except Exception as e:
        logger.error(f"Error running workflow: {e}")
        raise
    finally:
        DakoraIntegration.force_flush()
        await asyncio.sleep(0.5)
        await dakora.close()


async def run_workflow_with_devui() -> None:
    """
    Launch the workflow in DevUI for interactive testing.

    This allows you to test the workflow interactively and see
    how different inputs affect the routing and execution.
    All executions are still tracked in Dakora.
    """
    from agent_framework.devui import serve

    dakora = Dakora(base_url=BASE_URL, api_key=DAKORA_API_KEY)

    try:
        logger.info("=== Dakora + MAF Workflow DevUI ===\n")
        logger.info("Configuration:")
        logger.info(f"  Dakora Server: {BASE_URL}")
        logger.info(f"  OpenAI Model: {OPENAI_MODEL}\n")

        # Setup templates
        logger.info("Setting up workflow templates in Dakora...")
        await setup_workflow_templates(dakora)
        logger.info("Templates ready.\n")

        # Build workflow with Dakora tracking
        logger.info("Building workflow with Dakora-tracked agents...")
        workflow = await build_workflow_with_dakora()

        logger.info("\nStarting DevUI...")
        logger.info("Available at: http://localhost:8094")
        logger.info("\nThis workflow demonstrates:")
        logger.info("- All agents using Dakora templates for instructions")
        logger.info("- Conditional routing based on structured outputs")
        logger.info("- Path 1 (score >= 80): Reviewer → Publisher → Summarizer")
        logger.info("- Path 2 (score < 80): Reviewer → Editor → Publisher → Summarizer")
        logger.info("- All executions tracked in Dakora via OTEL")

        serve(entities=[workflow], port=8094, auto_open=True)

    except Exception as e:
        logger.error(f"Error launching DevUI: {e}")
        raise
    finally:
        # Cleanup happens when DevUI is closed
        pass


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Run Dakora + MAF Workflow Example"
    )
    parser.add_argument(
        "--devui",
        action="store_true",
        help="Launch workflow in DevUI for interactive testing"
    )
    args = parser.parse_args()

    if args.devui:
        asyncio.run(run_workflow_with_devui())
    else:
        asyncio.run(run_workflow_example())
