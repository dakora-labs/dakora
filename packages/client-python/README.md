# Dakora Python SDK

Centralized prompt management with versioning, execution tracking, and analytics for production LLM applications.

## Installation

```bash
pip install dakora-client
```

## Quick Start

```python
from dakora_client import Dakora

dakora = Dakora(api_key="dk_proj_...")

# Render versioned prompts
result = await dakora.prompts.render("greeting", {"name": "Alice"})
print(result.text)  # "Hello Alice! How can I help you today?"

# Use with agents (automatic tracking)
message = result.to_message()
response = await agent.run(message)

# Query execution history & analytics
executions = await dakora.executions.list(
    agent_id="support-bot"
)
```

**All executions automatically tracked** when using with [dakora-agents](../agents).

## Why Dakora?

- **Centralized Prompts** - Version control, A/B testing, instant updates without code deploys
- **Automatic Tracking** - Tokens, cost, latency tracked via OpenTelemetry
- **Template Linkage** - Know exactly which prompts are used in production
- **Built-in Analytics** - Query execution history by agent, session, template, cost

## Template Management

```python
# List prompts
prompts = await dakora.prompts.list(project_id="proj-123")

# Render with inputs
result = await dakora.prompts.render(
    prompt_id="support-response",
    inputs={"ticket": "...", "user": "Alice"}
)

# Version and metadata included
print(result.version)   # "2.1.0"
print(result.prompt_id) # "support-response"

# Convert to agent message (auto-tracking)
message = result.to_message()
```

## Execution Analytics

```python
# Filter by agent, session, template
executions = await dakora.executions.list(
    agent_id="support-bot",      # Specific agent
    session_id="session-789",    # User conversation
    prompt_id="greeting"         # Template used
)

# Calculate costs
total_cost = sum(e["cost_usd"] for e in executions)

# Get full details
execution = await dakora.executions.get(execution_id="trace-456")
print(execution["conversation_history"])
print(execution["templates_used"])
```

## Agent Integration

Automatic execution tracking with Microsoft Agent Framework:

```bash
pip install dakora-client[maf]
```

```python
from dakora_agents.maf import DakoraIntegration

middleware = DakoraIntegration.setup(dakora)
client = AzureOpenAIChatClient(..., middleware=[middleware])

# Every agent call automatically tracked:
# - Tokens (input/output)
# - Cost ($)
# - Latency (ms)
# - Template linkage
# - Conversation history
```

## Advanced Usage

**Pagination:**

```python
result = await dakora.executions.list(
    limit=50,
    offset=100,
    include_metadata=True
)

print(f"Showing {len(result['executions'])} of {result['total']}")
```

**Singleton pattern:**

```python
# config.py
from dakora_client import Dakora
dakora = Dakora()  # Uses DAKORA_API_KEY env var

# anywhere.py
from myapp.config import dakora
result = await dakora.prompts.render("greeting", {"name": "Alice"})
```

**Environment variables:**

```bash
DAKORA_API_KEY=dk_proj_...
DAKORA_BASE_URL=http://localhost:8000  # Optional
```

**FastAPI example:**

```python
from fastapi import FastAPI
from dakora_client import Dakora

dakora = Dakora()
app = FastAPI()

@app.get("/greet/{name}")
async def greet(name: str):
    result = await dakora.prompts.render("greeting", {"name": name})
    return {"message": result.text}
```

## Development

```bash
cd packages/client-python
pip install -e .
```