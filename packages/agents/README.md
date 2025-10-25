# Dakora Agents

Observability integrations for agent frameworks with Dakora.

## Overview

Provides automatic telemetry and observability for popular agent frameworks:

- **Microsoft Agent Framework (MAF)** - ✅ Available now
- **LangChain** - 🔜 Coming soon
- **CrewAI** - 🔜 Coming soon

Track execution metrics across all your agents:

- **Tokens**: Input and output token counts from LLM calls
- **Cost**: Execution cost in USD (calculated from token usage)
- **Latency**: Response time in milliseconds
- **Session Tracking**: Multi-agent workflows with session IDs
- **Full Context**: Input prompts and LLM responses

## Installation

```bash
# Install with MAF support
pip install dakora-agents[maf]

# Or install base package
pip install dakora-agents
```

## Quick Start (MAF)

```python
import asyncio
from agent_framework import ChatAgent
from agent_framework.openai import OpenAIChatClient
from dakora_client import Dakora
from dakora_agents.maf import create_dakora_middleware

async def main():
    # Initialize Dakora client
    dakora = Dakora(
        base_url="http://localhost:54321",
        api_key="dk_your_api_key"
    )
    
    # Get prompt template from Dakora
    instructions = await dakora.prompts.render("weather_agent_v1", {})
    
    # Create middleware
    middleware = create_dakora_middleware(
        dakora_client=dakora,
        prompt_id="weather_agent_v1",
        prompt_version="1.0.0",
    )
    
    # Create agent with middleware
    agent = ChatAgent(
        name="WeatherAgent",
        chat_client=OpenAIChatClient(),
        instructions=instructions,
        tools=[get_weather],
        middleware=[middleware]
    )
    
    # Run agent - metrics automatically logged to Dakora
    result = await agent.run("What's the weather in Seattle?")
    print(result)

asyncio.run(main())
```

## Multi-Agent Session Tracking

Track multiple agents working together:

```python
import uuid

# Generate session ID for this workflow
session_id = str(uuid.uuid4())

# Agent 1: Researcher
researcher = ChatAgent(
    name="Researcher",
    chat_client=OpenAIChatClient(),
    instructions=await dakora.prompts.render("research_prompt", {}),
    middleware=[
        create_dakora_middleware(
            dakora_client=dakora,
            prompt_id="research_prompt",
            session_id=session_id  # Same session ID
        )
    ]
)

# Agent 2: Writer
writer = ChatAgent(
    name="Writer",
    chat_client=OpenAIChatClient(),
    instructions=await dakora.prompts.render("writer_prompt", {}),
    middleware=[
        create_dakora_middleware(
            dakora_client=dakora,
            prompt_id="writer_prompt",
            session_id=session_id  # Same session ID
        )
    ]
)

# Run workflow - all activities tracked under same session
research = await researcher.run("Research quantum computing")
article = await writer.run(f"Write article: {research}")

# View in Dakora Studio: All prompts and metrics for this session
```

## Features

### Automatic Metrics Capture

- **Token Counting**: Extracts from `ChatResponse.usage_details`
- **Cost Calculation**: Uses provider-specific pricing tables
- **Latency Tracking**: Measures execution time
- **Provider Detection**: Identifies OpenAI, Azure, Anthropic, etc.

### Rich Context Logging

- **Input Prompt**: Full prompt sent to LLM
- **LLM Response**: Complete response received
- **Conversation ID**: Thread/conversation tracking
- **Agent ID**: Identify which agent executed

### Non-Blocking

Logging is asynchronous and won't slow down your agents. Failed logs won't crash your application.

## API Reference

### `create_dakora_middleware`

```python
def create_dakora_middleware(
    dakora_client: Dakora,
    prompt_id: str,
    prompt_version: str = "1.0.0",
    session_id: str | None = None,
    conversation_id: str | None = None,
) -> ChatMiddleware:
    """
    Create Dakora tracking middleware for MAF agents.
    
    Args:
        dakora_client: Initialized Dakora client
        prompt_id: ID of the Dakora prompt template
        prompt_version: Version of the prompt template
        session_id: Optional session ID for multi-agent tracking
        conversation_id: Optional conversation/thread ID
        
    Returns:
        ChatMiddleware instance ready to use with agents
    """
```

### `DakoraTrackingMiddleware`

Class-based middleware for advanced use cases:

```python
from dakora_agents.maf import DakoraTraceMiddleware

middleware = DakoraTraceMiddleware(
    dakora_client=dakora,
    project_id="my-project",
    agent_id="my-agent-v1",
    session_id=session_id,
)

agent = ChatAgent(
    chat_client=client,
    middleware=[middleware]
)
```

## Viewing Metrics in Dakora

After running your agents, view metrics in Dakora Studio:

1. Navigate to your prompt template
2. Click "Activity" tab
3. See all executions with:
   - Token usage and costs
   - Latency metrics
   - Success/failure rates
   - Full prompt and response logs

For multi-agent sessions:

1. Navigate to "Sessions" view
2. Find your session ID
3. See timeline of all agent activities

## Development

```bash
# Install in development mode
cd packages/agents
pip install -e ".[maf]"

# Run tests
pytest
```

## License

Apache 2.0
