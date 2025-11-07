# Dakora

<p align="center">
  <img src="assets/logo.svg" alt="Dakora Logo" width="400">
</p>

[![CI](https://github.com/dakora-labs/dakora/workflows/CI/badge.svg)](https://github.com/dakora-labs/dakora/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Discord](https://img.shields.io/discord/1422246380096720969?style=for-the-badge&color=667eea&label=Community&logo=discord&logoColor=white)](https://discord.gg/QSRRcFjzE8)

**Observability and prompt management for AI agents**

Built for [Microsoft Agent Framework](https://github.com/microsoft/agent-framework) with automatic tracing, cost tracking, and version-controlled prompts.

## Quick Start

**1. Get your API key**

Sign up at [playground.dakora.io](https://playground.dakora.io)

**2. Install**

```bash
pip install dakora-client[maf]
```

**3. Set environment variable**

```bash
export DAKORA_API_KEY="your_api_key"
```

**4. Add to your agent**

```python
from agent_framework import ChatAgent
from agent_framework.openai import OpenAIChatClient
from dakora_client import create_client
from dakora_agents.maf import create_dakora_middleware

# Initialize Dakora
dakora = create_client(api_key=os.getenv("DAKORA_API_KEY"))

# Get your prompt from Dakora
instructions = await dakora.prompts.render("my_agent_prompt", {})

# Add middleware to your agent
agent = ChatAgent(
    name="MyAgent",
    chat_client=OpenAIChatClient(),
    instructions=instructions.text,
    middleware=[
        create_dakora_middleware(
            dakora_client=dakora,
            instruction=instructions
        )
    ]
)

# Run - automatically tracked!
result = await agent.run("What's the weather?")
```

View traces, costs, and metrics at [playground.dakora.io](https://playground.dakora.io)

## Features

### Microsoft Agent Framework Integration

- **Native MAF middleware** - Drop-in observability for your agents
- **Deep visibility** - Trace agent execution, LLM calls, and tool usage
- **Built-in failure detection** - Automatic error tracking and alerts

### Prompt Management

- **Version control** - One-click rollback to any previous version
- **Reusable templates** - Jinja2-based with type-safe inputs
- **Live reload** - Update prompts without redeployment

### Cost Control & Observability

- **Real-time tracking** - Token usage and costs per execution
- **Spending caps** - Automatic kill switches when limits hit
- **Execution history** - Full metrics and debugging context

### Developer Experience

- **Python SDK & CLI** - Simple, intuitive APIs
- **`dakora start`** - Local development (like Supabase)
- **Project-scoped API keys** - Secure, team-friendly auth

## Multi-Agent Tracking

Track multiple agents working together with session IDs:

```python
import uuid

session_id = str(uuid.uuid4())

# Both agents share the same session
researcher = ChatAgent(
    middleware=[create_dakora_middleware(dakora, instruction=prompt1, session_id=session_id)]
)

writer = ChatAgent(
    middleware=[create_dakora_middleware(dakora, instruction=prompt2, session_id=session_id)]
)

# View the entire multi-agent workflow in Dakora Studio
```

## Local Development

Want to run Dakora locally instead of using the cloud?

```bash
pip install dakora
dakora start
```

This launches the full platform locally:
- **API**: http://localhost:54321
- **Studio**: http://localhost:3000

Then connect your SDK:
```python
dakora = create_client("http://localhost:54321")
```

## Documentation

- **[Quick Start Guide](https://docs.dakora.io/quickstart)** - Get started in 5 minutes
- **[MAF Integration](https://docs.dakora.io/integrations/maf)** - Deep dive into agent framework integration
- **[API Reference](https://docs.dakora.io/api)** - Complete SDK documentation
- **[Examples](examples/)** - Real-world integration examples

## Examples

See [`examples/`](examples/) for complete working examples:
- **[Microsoft Agent Framework](examples/microsoft-agent-framework/)** - Multi-agent orchestration with Dakora
- **[FastAPI + OpenAI](examples/openai-agents/)** - REST API with prompt templates

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Development setup
- Running tests
- Submitting pull requests

Join our community:
- **[Discord](https://discord.gg/QSRRcFjzE8)** - Get help and discuss
- **[GitHub Issues](https://github.com/dakora-labs/dakora/issues)** - Report bugs or request features
- **Email**: bogdan@dakora.io

## License

Apache-2.0 - See [LICENSE](LICENSE) for details.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.
