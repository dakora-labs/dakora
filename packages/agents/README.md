# Dakora Agents

OpenTelemetry observability for Microsoft Agent Framework with Dakora integration.

## Overview

Dakora Agents provides seamless observability for Microsoft Agent Framework via OpenTelemetry:

- **Budget Enforcement** - Automatic budget checking with caching
- **Template Linkage** - Track which Dakora prompts were used in executions
- **OTEL Native** - Leverages MAF's built-in OpenTelemetry support
- **Multi-Export** - Send traces to Dakora + Jaeger/Grafana/Azure Monitor
- **Zero Boilerplate** - One-line setup, automatic tracking

Automatically tracks:
- ✅ **Agent ID** - Which agent executed
- ✅ **Tokens** - Input and output token counts
- ✅ **Cost** - Calculated from token usage
- ✅ **Latency** - Response time in milliseconds
- ✅ **Conversation History** - Full input/output context
- ✅ **Template Linkage** - Which Dakora prompts were used

## Installation

```bash
pip install dakora-agents
```

Requires:
- `agent-framework` - Microsoft Agent Framework
- `dakora-client` - Dakora Python SDK
- `opentelemetry-api` and `opentelemetry-sdk` - OTEL core

## Quick Start

```python
from dakora_client import Dakora
from dakora_agents.maf import DakoraIntegration
from agent_framework.azure import AzureOpenAIChatClient

# 1. Initialize Dakora
dakora = Dakora(api_key="dkr_...")

# 2. One-line OTEL setup
middleware = DakoraIntegration.setup(dakora)

# 3. Use with any MAF client
azure_client = AzureOpenAIChatClient(
    endpoint=...,
    deployment_name=...,
    api_key=...,
    middleware=[middleware],
)

# 4. Run agents - everything auto-tracked!
agent = azure_client.create_agent(
    id="chat-v1",
    name="ChatBot",
    instructions="You are helpful.",
)

response = await agent.run("Hello!")
```

**That's it!** Dakora automatically tracks:
- Budget (checked before execution)
- Agent ID
- Tokens (input + output)
- Latency
- Conversation history

## Template Linkage

Link executions to Dakora templates:

```python
# Render template from Dakora
greeting = await dakora.prompts.render("greeting", {"name": "Alice"})

# Create agent with template
agent = azure_client.create_agent(
    id="chat-v1",
    instructions=greeting.text,  # Use rendered text
)

# Run with template-linked message
response = await agent.run(greeting.to_message())
```

The execution will be linked to the `greeting` template in Dakora Studio!

## Multi-Export

Send traces to multiple backends:

```python
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

middleware = DakoraIntegration.setup(
    dakora,
    additional_exporters=[
        OTLPSpanExporter(endpoint="http://localhost:4317")  # Jaeger
    ]
)

# Now traces go to BOTH Dakora and Jaeger!
```

Or use convenience methods:

```python
# Dakora + Jaeger
middleware = DakoraIntegration.setup_with_jaeger(dakora)

# Dakora + Azure Monitor
middleware = DakoraIntegration.setup_with_azure_monitor(
    dakora,
    connection_string="..."
)
```

## Examples

See `examples/quickstart.py` for complete examples:
- Basic usage
- Template linkage
- Multi-agent pipelines
- Jaeger integration

##Migration Guide (from v1.x)

### Before (old API)

```python
from dakora_agents.maf import create_dakora_middleware

middleware = create_dakora_middleware(
    dakora_client=dakora,
    session_id="session-123",
    instruction_template=...,
)
```

### After (new API)

```python
from dakora_agents.maf import DakoraIntegration

middleware = DakoraIntegration.setup(dakora)

# Templates now use to_message()
template = await dakora.prompts.render("greeting", {...})
agent = client.create_agent(instructions=template.text)
await agent.run(template.to_message())
```

**Breaking Changes:**
- `create_dakora_middleware()` removed (use `DakoraIntegration.setup()`)
- `session_id` parameter removed (now optional via span attributes)
- `instruction_template` parameter removed (use `to_message()`)

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
