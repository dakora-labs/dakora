# Dakora Agents

Observability integrations for agent frameworks.

## Overview

Automatic telemetry for popular agent frameworks:
- **Microsoft Agent Framework (MAF)** - ✅ Available now
- **LangChain** - 🔜 Coming soon
- **CrewAI** - 🔜 Coming soon

Track tokens, costs, latency, and full execution context across all your agents.

## Installation

```bash
# With MAF support
pip install dakora-agents[maf]

# Base package
pip install dakora-agents
```

## Quick Start (MAF)

```python
from agent_framework import ChatAgent
from agent_framework.openai import OpenAIChatClient
from dakora_client import create_client
from dakora_agents.maf import create_dakora_middleware

async def main():
    # Initialize Dakora
    dakora = create_client("http://localhost:54321", api_key="dk_xxx")

    # Render prompt template
    instructions = await dakora.prompts.render("weather_agent_v1", {})

    # Create middleware
    middleware = create_dakora_middleware(
        dakora_client=dakora,
        instruction=instructions,
    )

    # Create agent with middleware
    agent = ChatAgent(
        name="WeatherAgent",
        chat_client=OpenAIChatClient(),
        instructions=instructions.text,
        middleware=[middleware],
    )

    # Run agent - metrics automatically logged
    result = await agent.run("What's the weather in Seattle?")
```

## Features

- **Automatic metrics**: Token counts, costs, latency
- **Full context**: Input prompts and LLM responses
- **Session tracking**: Multi-agent workflow support
- **Non-blocking**: Async logging won't slow down agents

## Documentation

See the [full documentation](https://docs.dakora.io) for:
- Multi-agent session tracking
- Advanced middleware configuration
- Viewing metrics in Dakora Studio
- Integration examples

## Development

```bash
cd packages/agents
pip install -e ".[maf]"
pytest
```