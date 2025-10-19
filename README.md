# Dakora

<p align="center">
  <img src="assets/logo.svg" alt="Dakora Logo" width="200">
</p>

[![CI](https://github.com/bogdan-pistol/dakora/workflows/CI/badge.svg)](https://github.com/bogdan-pistol/dakora/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Discord](https://img.shields.io/discord/1422246380096720969?style=for-the-badge&color=667eea&label=Community&logo=discord&logoColor=white)](https://discord.gg/QSRRcFjzE8)

**AI Control Plane for Prompt Management**

A platform for managing and executing LLM prompts with type-safe inputs, versioning, and multi-model comparison. Run locally with Docker or connect to the cloud.

## 🚀 Quick Start

### Install CLI

```bash
pip install dakora
```

### Initialize Project

```bash
dakora init
```

### Start Platform

```bash
dakora start
```

This launches:
- **API** at http://localhost:54321
- **Studio UI** at http://localhost:3000

### Use in Your App

```bash
pip install dakora-client
```

```python
from dakora_client import create_client

dakora = create_client("http://localhost:54321")

# List templates
templates = await dakora.prompts.list()

# Render template
result = await dakora.prompts.render(
    "summarizer",
    inputs={"text": "Your article here..."}
)

print(result.rendered)
```

## Features

- 🎯 **Docker-first architecture** - Runs locally or in the cloud
- 🚀 **LLM Execution** - Run templates against 100+ providers (OpenAI, Anthropic, Google)
- 🎨 **Type-safe prompt templates** with validation
- 📁 **File-based template management** with YAML
- 🔄 **Hot-reload support** for development
- 📝 **Jinja2 templating** with custom filters
- 💰 **Cost & performance tracking** - Monitor tokens, latency, and costs
- 🖥️ **Modern Studio UI** - Interactive web interface for template development
- 🧵 **Thread-safe** for production use
- 🌐 **Multi-language SDKs** - Python, TypeScript (coming soon), Go (coming soon)

## Repository Structure

```
dakora/                         # Monorepo root
├── server/                     # Platform backend (Docker)
│   ├── dakora_server/
│   │   ├── api/                # API routes
│   │   ├── core/               # Business logic
│   │   └── main.py             # FastAPI app
│   ├── Dockerfile
│   └── pyproject.toml
│
├── packages/                   # Multi-language SDKs
│   ├── client-python/          # Python SDK
│   │   └── dakora_client/
│   └── client-typescript/      # TypeScript SDK (coming soon)
│
├── studio/                     # Dashboard UI (React)
│   ├── src/
│   ├── Dockerfile
│   └── package.json
│
├── cli/                        # Minimal CLI
│   └── dakora_cli/
│
├── docker/                     # Docker Compose
│   └── docker-compose.yml
│
└── prompts/                    # Your templates
```

## Python SDK

### Installation

```bash
pip install dakora-client
```

### Usage

```python
from dakora_client import create_client

# Local (Docker)
dakora = create_client("http://localhost:54321")

# Cloud
dakora = create_client("https://api.dakora.cloud", api_key="dk_xxx")

# List templates
templates = await dakora.prompts.list()

# Get template details
template = await dakora.prompts.get("summarizer")

# Render template
result = await dakora.prompts.render(
    "summarizer",
    inputs={"text": "Article to summarize..."}
)

# Compare multiple models
comparison = await dakora.prompts.compare(
    "summarizer",
    models=["gpt-4", "claude-3-opus", "gemini-pro"],
    inputs={"text": "Article..."},
    temperature=0.7
)

# Close connection
await dakora.close()
```

### Context Manager

```python
async with create_client("http://localhost:54321") as dakora:
    result = await dakora.prompts.render("greeting", {"name": "Alice"})
    print(result.rendered)
```

## CLI Commands

```bash
# Initialize new project
dakora init

# Start platform (Docker Compose)
dakora start

# Stop platform
dakora stop

# Link to cloud instance
dakora link https://api.dakora.cloud

# Show version
dakora version
```

## Template Format

Create templates as YAML files in the `prompts/` directory:

```yaml
id: greeting
version: 1.0.0
description: A personalized greeting template
template: |
  Hello {{ name }}!
  {% if age %}You are {{ age }} years old.{% endif %}
  {{ message | default("Have a great day!") }}
inputs:
  name:
    type: string
    required: true
  age:
    type: number
    required: false
  message:
    type: string
    required: false
    default: "Welcome to Dakora!"
metadata:
  tags: ["greeting", "example"]
```

### Supported Input Types

- `string` - Text values
- `number` - Numeric values (int/float)
- `boolean` - True/false values
- `array<string>` - List of strings
- `object` - Dictionary/JSON object

## API Reference

### REST API

The Dakora server exposes a REST API:

**Templates:**
- `GET /api/templates` - List all templates
- `GET /api/templates/{id}` - Get template details
- `POST /api/templates` - Create template
- `PUT /api/templates/{id}` - Update template
- `POST /api/templates/{id}/render` - Render template
- `POST /api/templates/{id}/compare` - Compare LLM outputs

**Health:**
- `GET /api/health` - Health check

## Docker Setup

### Local Development

```bash
# Initialize project
dakora init

# Start all services
dakora start

# Or manually with Docker Compose
cd docker
docker compose up -d
```

### Services

- **api** - FastAPI server (port 54321)
- **studio** - React UI (port 3000)
- **db** - PostgreSQL database (port 5432)
- **redis** - Redis cache (port 6379)

### Environment Variables

Create `.env` file:

```bash
MODE=local
API_PORT=54321
STUDIO_PORT=3000
```

## LLM Execution

### Setting API Keys

Set environment variables for your LLM providers:

```bash
export OPENAI_API_KEY="your_key_here"
export ANTHROPIC_API_KEY="your_key_here"
export GOOGLE_API_KEY="your_key_here"
```

Or in `.env` file:

```bash
OPENAI_API_KEY="your_key_here"
ANTHROPIC_API_KEY="your_key_here"
GOOGLE_API_KEY="your_key_here"
```

**Never commit API keys to version control!**

### Compare Multiple Models

```python
from dakora_client import create_client

async with create_client("http://localhost:54321") as dakora:
    comparison = await dakora.prompts.compare(
        "summarizer",
        models=["gpt-4", "claude-3-opus", "gemini-pro"],
        inputs={"text": "Your article content here..."},
        temperature=0.7
    )

    for result in comparison.results:
        print(f"{result.model}: ${result.cost_usd:.4f} ({result.latency_ms}ms)")
```

### Supported Models

Dakora supports 100+ LLM providers through LiteLLM:

- **OpenAI:** `gpt-4`, `gpt-4-turbo`, `gpt-3.5-turbo`
- **Anthropic:** `claude-3-opus`, `claude-3-sonnet`, `claude-3-haiku`
- **Google:** `gemini-pro`, `gemini-1.5-pro`
- **Local:** `ollama/llama3`, `ollama/mistral`

See [LiteLLM docs](https://docs.litellm.ai/docs/providers) for the full list.

## Azure Blob Storage

Store templates in Azure Blob Storage:

```yaml
# dakora.yaml (server config)
registry: azure
azure_container: prompts
azure_account_url: https://myaccount.blob.core.windows.net
logging:
  enabled: true
  backend: sqlite
  db_path: ./dakora.db
```

Install with Azure support:

```bash
# Server
cd server
pip install -e ".[azure]"
```

## Development

### Prerequisites

- Python 3.11+
- Node.js 20+ (for Studio UI)
- Docker & Docker Compose
- uv (Python package manager)

### Setup

```bash
git clone https://github.com/bogdan-pistol/dakora.git
cd dakora

# Install dependencies
uv sync

# Build Studio UI
cd studio
npm install
npm run build

# Start platform
cd ..
dakora start
```

### Project Structure

- `server/` - FastAPI backend
- `packages/client-python/` - Python SDK
- `studio/` - React frontend
- `cli/` - CLI tool
- `docker/` - Docker infrastructure

### Running Tests

```bash
cd server
uv run pytest
```

## Contributing

We welcome contributions! Join our community:

- 💬 **[Discord](https://discord.gg/QSRRcFjzE8)** - Discussions and support
- 🐛 **Issues** - Report bugs or request features
- 🔀 **Pull Requests** - Submit improvements

### Development Setup

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and add tests
4. Run the test suite: `cd server && uv run pytest`
5. Submit a pull request

## Roadmap

- [ ] TypeScript SDK (`@dakora/client`)
- [ ] Go SDK (`github.com/dakora/dakora-go`)
- [ ] Cloud hosting (SaaS)
- [ ] Team collaboration features
- [ ] Template marketplace
- [ ] Advanced analytics

## License

Apache-2.0 License - see [LICENSE](LICENSE) file for details.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.