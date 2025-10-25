"""
Example: Using Dakora MAF Middleware to track agent executions

This example shows how to use Dakora prompts with Microsoft Agent Framework
and automatically track all executions (tokens, cost, latency) back to Dakora.

Prerequisites:
    pip install dakora-agents[maf]
    # OR install dependencies separately:
    pip install dakora-client agent-framework-core httpx

Quick Start:
1. Install dependencies (see above)
2. Update BASE_URL, PROJECT_ID, and API_KEY at the top of this file
3. Start your Dakora server: uvicorn dakora_server.main:app --reload --port 54321
4. Run: python maf_integration_example.py
5. Templates will be created automatically
6. Uncomment the example functions in main() to run them
"""

import asyncio
import uuid
from agent_framework import ChatAgent
from agent_framework.openai import OpenAIChatClient
from dakora_client import Dakora
from dakora_agents.maf import create_dakora_middleware, to_message


# ============================================================================
# CONFIGURATION - UPDATE THESE VALUES
# ============================================================================
BASE_URL = "http://localhost:8000"  # Your Dakora server URL
PROJECT_ID = "73996404-48e2-4e53-bd6d-ce9e30b4f887"  # Get this from Dakora Studio
API_KEY = "dkr_CRSkoqK4EczNvyL6hWiR1eqKxqpdoMterisLK3K3AN9d"  # Optional: your API key

# OpenAI Configuration
# Set your OpenAI API key via environment variable: OPENAI_API_KEY
# Or configure Azure OpenAI via: AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT
OPENAI_MODEL = "gpt-4o-mini"  # Model to use for examples


# Example template definitions
TEMPLATES = {
    "weather_agent_instructions": {
        "id": "weather_agent_instructions",
        "version": "1.0.0",
        "description": "System instructions for a weather information agent",
        "template": """You are a helpful weather assistant. Provide accurate weather information and forecasts.
When users ask about weather, be concise but informative.""",
        "inputs": {},
        "metadata": {"category": "agent-instructions", "framework": "maf"}
    },
    "research_agent_instructions": {
        "id": "research_agent_instructions",
        "version": "1.0.0",
        "description": "Instructions for a research agent",
        "template": """You are a thorough research agent. Gather comprehensive information and organize findings clearly.""",
        "inputs": {},
        "metadata": {"category": "agent-instructions"}
    },
    "writer_agent_instructions": {
        "id": "writer_agent_instructions",
        "version": "1.0.0",
        "description": "Instructions for a writer agent",
        "template": """You are a skilled content writer. Transform research into clear, engaging content.""",
        "inputs": {},
        "metadata": {"category": "agent-instructions"}
    },
    "assistant_instructions": {
        "id": "assistant_instructions",
        "version": "1.0.0",
        "description": "General assistant instructions",
        "template": """You are a helpful AI assistant. Provide accurate, friendly, and relevant responses.""",
        "inputs": {},
        "metadata": {"category": "agent-instructions"}
    },
    "weather_query_template": {
        "id": "weather_query_template",
        "version": "1.0.0",
        "description": "Template for weather queries with parameters",
        "template": "I need weather information for {{city}}. Please provide {{details}}.",
        "inputs": {
            "city": {"type": "string", "required": True},
            "details": {"type": "string", "required": True, "default": "current conditions"}
        },
        "metadata": {"category": "user-prompts"}
    }
}


async def setup_templates(base_url: str, project_id: str, api_key: str | None = None):
    """
    Create example templates in Dakora if they don't exist.
    
    This helper function creates the templates needed for the examples.
    In production, you'd manage templates through Dakora Studio.
    """
    dakora = Dakora(base_url=base_url, api_key=api_key, project_id=project_id)
    
    for template_id, template_data in TEMPLATES.items():
        try:
            # Check if template exists
            try:
                await dakora.prompts.get(template_id)
                print(f"✓ Template '{template_id}' already exists")
                continue
            except Exception:
                # Template doesn't exist, create it
                pass
            
            # Create template
            await dakora.prompts.create(
                prompt_id=template_data["id"],
                version=template_data["version"],
                description=template_data.get("description"),
                template=template_data["template"],
                inputs=template_data.get("inputs", {}),
                metadata=template_data.get("metadata", {})
            )
            print(f"✓ Created template '{template_id}'")
                
        except Exception as e:
            print(f"⚠ Error setting up '{template_id}': {e}")


async def simple_agent_example():
    """
    Simple example with a single agent using Dakora templates.
    
    This shows how to use a Dakora template for agent instructions
    with automatic observability tracking.
    """
    
    # Initialize Dakora client
    dakora = Dakora(base_url=BASE_URL, api_key=API_KEY)
    
    # Get prompt template from Dakora for agent instructions
    instructions_result = await dakora.prompts.render("weather_agent_instructions", {})
    
    print(f"Using Dakora template: weather_agent_instructions")
    print(f"Template version: {instructions_result.version}")
    print(f"Instructions: {instructions_result.text[:100]}...")
    
    # Create middleware to track executions
    middleware = create_dakora_middleware(
        dakora_client=dakora,
        project_id=PROJECT_ID,
        agent_id="weather_agent",
    )
    
    # Create agent with Dakora template as instructions
    agent = ChatAgent(
        name="WeatherAgent",
        chat_client=OpenAIChatClient(model_id=OPENAI_MODEL),
        instructions=instructions_result.text,  # Use template text for instructions
        middleware=[middleware]
    )
    
    # Run agent - metrics automatically logged to Dakora!
    result = await agent.run("What's the weather like in Seattle?")
    print(f"\nAgent response: {result}")
    print("\n✅ Execution metrics logged to Dakora!")
    print(f"   View in Dakora Studio → Projects → {PROJECT_ID} → Traces")


async def template_tracking_example():
    """
    Advanced example with full template tracking in messages.
    
    This example shows how to:
    1. Use Dakora templates for agent instructions
    2. Use to_message() to track template usage in conversation messages
    3. Link traces back to specific template versions in Dakora Studio
    """
    
    # Initialize Dakora client
    dakora = Dakora(base_url=BASE_URL, api_key=API_KEY)
    
    # Get instruction template from Dakora
    instructions_result = await dakora.prompts.render("weather_agent_instructions", {})
    
    # Get a user prompt template (e.g., for consistent user queries)
    user_prompt_result = await dakora.prompts.render(
        "weather_query_template",
        {"city": "Seattle", "details": "temperature and conditions"}
    )
    
    print(f"Using Dakora templates:")
    print(f"  Instructions: weather_agent_instructions v{instructions_result.version}")
    print(f"  User prompt: weather_query_template v{user_prompt_result.version}")
    
    # Create middleware
    middleware = create_dakora_middleware(
        dakora_client=dakora,
        project_id=PROJECT_ID,
        agent_id="weather_agent",
    )
    
    # Create agent with Dakora template as instructions
    agent = ChatAgent(
        name="WeatherAgent",
        chat_client=OpenAIChatClient(model_id=OPENAI_MODEL),
        instructions=instructions_result.text,  # Template text for instructions
        middleware=[middleware]
    )
    
    # Use to_message() to convert template result to message with metadata
    # This preserves prompt_id, version, and inputs in the trace
    user_message = to_message(user_prompt_result)
    
    # Run agent with template-tracked message
    # The trace will link to BOTH templates (instructions + user message) in Dakora
    result = await agent.run([user_message])
    print(f"\nAgent response: {result}")
    print("\n✅ Execution logged with full template tracking!")
    print(f"   Trace includes:")
    print(f"     - Template: weather_query_template v{user_prompt_result.version}")
    print(f"     - Inputs: {user_prompt_result.inputs}")
    print("   View in Dakora Studio → Prompts → weather_query_template → Activity tab")


async def multi_agent_example():
    """
    Multi-agent workflow example with session tracking.
    
    This shows how to:
    1. Use Dakora templates for multiple agents
    2. Track agents working together under a single session ID
    3. See the complete multi-agent workflow in Dakora Studio
    """
    
    # Initialize Dakora
    dakora = Dakora(base_url=BASE_URL, api_key=API_KEY)
    
    # Generate unique session ID for this workflow
    session_id = str(uuid.uuid4())
    
    print(f"Starting multi-agent workflow with session: {session_id}")
    
    # Agent 1: Researcher (uses "research_prompt" template from Dakora)
    researcher_instructions = await dakora.prompts.render("research_agent_instructions", {})
    researcher = ChatAgent(
        name="Researcher",
        chat_client=OpenAIChatClient(model_id=OPENAI_MODEL),
        instructions=researcher_instructions.text,  # Use Dakora template
        middleware=[
            create_dakora_middleware(
                dakora_client=dakora,
                project_id=PROJECT_ID,
                session_id=session_id,  # Same session for all agents
                agent_id="researcher"
            )
        ]
    )
    
    # Agent 2: Writer (uses "writer_prompt" template from Dakora)
    writer_instructions = await dakora.prompts.render("writer_agent_instructions", {})
    writer = ChatAgent(
        name="Writer",
        chat_client=OpenAIChatClient(model_id=OPENAI_MODEL),
        instructions=writer_instructions.text,  # Use Dakora template
        middleware=[
            create_dakora_middleware(
                dakora_client=dakora,
                project_id=PROJECT_ID,
                session_id=session_id,  # Same session
                agent_id="writer"
            )
        ]
    )
    
    # Run multi-agent workflow
    print("\n1. Research phase...")
    research = await researcher.run("Research quantum computing basics")
    print(f"Research complete: {str(research)[:100]}...")
    
    print("\n2. Writing phase...")
    article = await writer.run(f"Write a brief article based on: {research}")
    print(f"Article complete: {str(article)[:100]}...")
    
    print("\n✅ Multi-agent workflow complete!")
    print("   Both agents used Dakora templates for instructions")
    print("   View session in Dakora Studio:")
    print(f"   Sessions → {session_id}")
    print("   See all agents, templates used, tokens, costs, and timeline")


async def with_conversation_tracking():
    """
    Example with conversation/thread tracking using Dakora templates.
    
    Shows how to:
    1. Use Dakora templates for agent instructions
    2. Track multiple turns in the same conversation
    3. Use session_id to group related interactions
    """
    
    dakora = Dakora(base_url=BASE_URL, api_key=API_KEY)
    conversation_id = f"conv-{uuid.uuid4()}"
    
    # Fetch instruction template from Dakora
    assistant_instructions = await dakora.prompts.render("assistant_instructions", {})
    
    # Create agent with Dakora template and conversation tracking
    agent = ChatAgent(
        name="Assistant",
        chat_client=OpenAIChatClient(model_id=OPENAI_MODEL),
        instructions=assistant_instructions.text,  # Use Dakora template
        middleware=[
            create_dakora_middleware(
                dakora_client=dakora,
                project_id=PROJECT_ID,
                session_id=conversation_id  # Track conversation
            )
        ]
    )
    
    # Multiple turns in same conversation
    print(f"Starting conversation: {conversation_id}")
    print(f"Using Dakora template: assistant_instructions v{assistant_instructions.version}")
    
    result1 = await agent.run("Hi, what can you help me with?")
    print(f"Turn 1: {result1}")
    
    result2 = await agent.run("Tell me about Python")
    print(f"Turn 2: {result2}")
    
    print(f"\n✅ All turns logged under conversation: {conversation_id}")
    print("   Agent used Dakora template for consistent behavior")
    print("   View conversation history in Dakora Studio")



if __name__ == "__main__":
    print("=== Dakora MAF Middleware Examples ===\n")
    print(f"Configuration:")
    print(f"  Server: {BASE_URL}")
    print(f"  Project: {PROJECT_ID}")
    print(f"  API Key: {'***' + API_KEY[-4:] if API_KEY else 'None'}")
    print()
    
    # Setup: Create example templates
    print("Setting up example templates...")
    asyncio.run(setup_templates(BASE_URL, PROJECT_ID, API_KEY))
    print()
    
    print("✅ Setup complete! Uncomment examples below to run them.\n")
    
    # Uncomment to run examples:
    
    # # Run simple example
    # print("\n--- Example 1: Simple Agent ---")
    asyncio.run(simple_agent_example())
    
    # # Run template tracking example
    # print("\n\n--- Example 2: Template Tracking ---")
    asyncio.run(template_tracking_example())
    
    # # Run multi-agent example
    # print("\n\n--- Example 3: Multi-Agent Workflow ---")
    asyncio.run(multi_agent_example())
    
    # # Run conversation example
    # print("\n\n--- Example 4: Conversation Tracking ---")
    asyncio.run(with_conversation_tracking())
