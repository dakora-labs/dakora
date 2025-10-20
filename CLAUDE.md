# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Dakora is an AI Control Plane for managing prompt templates with type-safe inputs, versioning, multi-model LLM execution, and comparison capabilities. The project is organized as a **monorepo** with the following packages:

- **Server** (`server/`): FastAPI-based platform backend with REST API
- **Client SDK** (`packages/client-python/`): Python client library for interacting with the API
- **CLI** (`cli/`): Minimal command-line tool for managing the platform
- **Studio** (`studio/`): React-based web UI for template development and testing
- **Docker** (`docker/`): Docker Compose configuration for local deployment

## Architecture

### Server (`server/dakora_server/`)

**Main Entry Point:**
- `main.py` - FastAPI application factory with CORS middleware, API routes, and Studio static file serving

**Configuration:**
- `config.py` - Pydantic settings with environment variables, vault singleton pattern

**API Routes (`api/`):**
- `prompts.py` - Template CRUD operations (list, get, create, update)
- `render.py` - Template rendering endpoint
- `models.py` - Multi-model comparison endpoint (`/api/templates/{id}/compare`)
- `health.py` - Health check endpoint
- `schemas.py` - Pydantic request/response models

**Core Business Logic (`core/`):**

**Vault System:**
- `vault.py` - Main Vault class with thread-safe caching (RLock), registry integration, template management
- Supports multiple initialization patterns:
  - Direct registry injection: `Vault(LocalRegistry("./prompts"))`
  - Azure storage: `Vault(AzureRegistry(container="prompts", ...))`
  - Legacy config file: `Vault.from_config("promptvault.yaml")`

**Template System:**
- `model.py` - Pydantic models for templates:
  - `TemplateSpec` - Template definition with id, version, description, template, inputs, metadata
  - `InputSpec` - Input field specification with type validation and coercion
  - Supported input types: string, number, boolean, array&lt;string&gt;, object
- `renderer.py` - Jinja2-based template rendering with custom filters

**Registry System (`registry/`):**
- `base.py` - Abstract Registry protocol
- `core.py` - TemplateRegistry with pluggable storage backends
- `backends/` - Storage backend implementations:
  - `base.py` - StorageBackend protocol
  - `local.py` - Local filesystem backend
  - `azure.py` - Azure Blob Storage backend
- `implementations/` - High-level registry implementations:
  - `local.py` - LocalRegistry
  - `azure.py` - AzureRegistry
- `serialization.py` - YAML parsing and rendering utilities

**LLM Integration (`llm/`):**
- `client.py` - LLMClient using litellm for multi-provider LLM support
  - `execute()` - Synchronous single model execution
  - `_execute_async()` - Asynchronous execution with error handling
- `models.py` - Data models:
  - `ExecutionResult` - Single model execution result (output, tokens, cost, latency)
  - `ComparisonResult` - Multi-model comparison result

**Utilities:**
- `types.py` - Type definitions (InputType, etc.)
- `exceptions.py` - Custom exception hierarchy (DakoraError, TemplateNotFound, ValidationError, etc.)
- `logging.py` - SQLite-based execution logging
- `watcher.py` - File system monitoring for hot-reload

**Dependencies:**
- FastAPI + Uvicorn - Web framework
- Pydantic - Data validation
- Jinja2 - Template rendering
- litellm - Multi-provider LLM integration
- PyYAML - Template storage format
- Watchdog - File system monitoring
- Azure SDK (optional) - Cloud storage

### Client SDK (`packages/client-python/dakora_client/`)

**Package:** `dakora-client` (published to PyPI)

**Structure:**
- `client.py` - Main `Dakora` class with async HTTP client (httpx)
- `prompts.py` - `PromptsAPI` class with methods:
  - `list()` - List all template IDs
  - `get(template_id)` - Get template details
  - `create(...)` - Create new template
  - `update(template_id, ...)` - Update existing template
  - `render(template_id, inputs)` - Render template with inputs
  - `compare(template_id, models, inputs, ...)` - Compare across multiple LLM models
- `types.py` - Data models (TemplateInfo, RenderResult, CompareResult)

**Usage Example:**
```python
from dakora_client import Dakora

# Local (Docker)
dakora = Dakora("http://localhost:54321")
templates = await dakora.prompts.list()
result = await dakora.prompts.render("greeting", {"name": "Alice"})

# Cloud
dakora = Dakora("https://api.dakora.cloud", api_key="dk_xxx")
comparison = await dakora.prompts.compare(
    "greeting",
    models=["gpt-4", "claude-3-opus"],
    inputs={"name": "Alice"}
)
```

### CLI (`cli/dakora_cli/`)

**Package:** `dakora` (published to PyPI)

**Commands:**
- `dakora start` - Start platform via Docker Compose (defaults to detached mode)
- `dakora stop` - Stop platform
- `dakora init` - Initialize new project with example templates
- `dakora link <url>` - Link to cloud Dakora instance
- `dakora version` - Show CLI version

**Features:**
- Auto-detects docker-compose.yml in multiple locations
- Falls back to embedded template if no local compose file found
- Creates example template on init

### Studio (`studio/`)

**Tech Stack:**
- React 18 + TypeScript
- Vite - Build tool
- React Router - Client-side routing
- shadcn/ui - Component library
- Tailwind CSS - Styling

**Structure:**
```
studio/src/
├── App.tsx                  # Main app with routing
├── components/
│   ├── layout/
│   │   ├── MainLayout.tsx   # Layout container
│   │   ├── TopBar.tsx       # Top navigation
│   │   └── Sidebar.tsx      # Collapsible sidebar
│   ├── PromptList.tsx       # Template list component
│   ├── PromptEditor.tsx     # Template editing component
│   ├── StatusBar.tsx        # Footer status bar
│   ├── NewPromptDialog.tsx  # New template dialog
│   └── ui/                  # shadcn/ui components
├── pages/
│   ├── DashboardPage.tsx    # Template browser with search
│   ├── PromptEditPage.tsx   # Template editor
│   └── NewPromptPage.tsx    # New template creation
├── views/
│   ├── PromptsView.tsx      # Prompts tab view
│   └── ExecuteView.tsx      # Execution/comparison view
├── hooks/
│   └── useApi.ts            # API client hooks
└── utils/
    └── api.ts               # API utility functions
```

**Build Process:**
- Runs `npm run build` in studio/
- Outputs to `studio/dist/`
- Server serves static files from dist/ in production
- Nginx serves UI in Docker with API proxy

### Docker (`docker/`)

**Services:**
- `api` - Dakora server (port 54321)
- `studio` - Studio UI via nginx (port 3000)
- `db` - PostgreSQL 15
- `redis` - Redis 7

**Configuration:**
- `.env.example` - Environment template
- Default ports: API (54321), Studio (3000)
- Volumes: prompts directory mounted read-only

## Development Workflow

### Environment Setup

```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies
export PATH="$HOME/.local/bin:$PATH" && uv sync

# Run server during development
cd server
export PATH="$HOME/.local/bin:$PATH" && uv run uvicorn dakora_server.main:app --reload --port 8000
```

### Testing the Server

```bash
# Run all tests
export PATH="$HOME/.local/bin:$PATH" && uv run python -m pytest

# Run specific test categories
export PATH="$HOME/.local/bin:$PATH" && uv run python server/tests/test_runner.py unit
export PATH="$HOME/.local/bin:$PATH" && uv run python server/tests/test_runner.py integration
export PATH="$HOME/.local/bin:$PATH" && uv run python server/tests/test_runner.py performance

# Run specific test file
export PATH="$HOME/.local/bin:$PATH" && uv run python -m pytest server/tests/test_vault_execute.py -v

# Quick validation
python validate_tests.py
```

### Running the Platform

```bash
# Start via Docker (recommended)
dakora start

# Or manually start server for development
cd server
export PATH="$HOME/.local/bin:$PATH" && uv run uvicorn dakora_server.main:app --reload --port 8000

# Build Studio UI
cd studio
npm run build

# Studio development server (optional)
cd studio
npm run dev
```

### API Key Configuration

Dakora integrates with LLM providers for model execution and comparison.

**Setup:**
1. Create `.env` file in project root
2. Add required API keys:
```bash
OPENAI_API_KEY="sk-..."
ANTHROPIC_API_KEY="sk-ant-..."
```

**Supported Providers:**
- OpenAI (GPT-3.5, GPT-4)
- Anthropic (Claude)
- Any provider supported by litellm

### Working with Templates

Templates are stored as YAML files with this structure:

```yaml
id: greeting
version: 1.0.0
description: A simple greeting template
template: |
  Hello {{ name }}!
  {% if message %}{{ message }}{% endif %}
inputs:
  name:
    type: string
    required: true
  message:
    type: string
    required: false
    default: "Welcome to Dakora!"
metadata:
  tags: ["example", "greeting"]
```

**Input Types:**
- `string` - Text values
- `number` - Numeric values (int or float)
- `boolean` - true/false values
- `array<string>` - List of strings
- `object` - Dictionary/object values

**Template Features:**
- Jinja2 syntax for logic and loops
- Custom filters: `yaml`, `default`
- Type coercion and validation on render
- Default values for optional inputs

## Key Features

### Multi-Model LLM Execution

Templates can be executed with LLM models and compared across providers:

```python
# Single execution
result = await template.execute("gpt-4", **inputs)

# Compare across models
comparison = await template.compare(
    models=["gpt-4", "claude-3-opus", "gpt-3.5-turbo"],
    **inputs
)
```

**Comparison Features:**
- Parallel execution for speed
- Error handling per model
- Token usage and cost tracking
- Latency measurements

### Azure Storage Support

Templates can be stored in Azure Blob Storage:

```python
from dakora_server.core.registry import AzureRegistry
from dakora_server.core.vault import Vault

vault = Vault(AzureRegistry(
    container="prompts",
    account_url="https://account.blob.core.windows.net",
    # Optional: credential (defaults to DefaultAzureCredential)
))
```

**Features:**
- Connection string or DefaultAzureCredential support
- Automatic YAML file discovery
- Same API as local registry

### File Watching

The watcher monitors template directory for changes and invalidates cache:

```python
from dakora_server.core.watcher import Watcher

watcher = Watcher(prompt_dir, callback=lambda: vault.invalidate_cache())
watcher.start()
```

## Testing Strategy

**Test Organization:**
- `server/tests/` - All server tests
- Test categories: unit, integration, performance
- Manual tests for LLM functionality (require API keys)

**Key Test Files:**
- `test_vault_execute.py` - LLM execution tests
- `test_vault_compare.py` - Multi-model comparison tests
- `test_llm_client.py` - LLM client unit tests
- `test_registry_azure.py` - Azure storage tests
- `conftest.py` - Pytest fixtures

**Running Specific Tests:**
```bash
# LLM execution tests (requires API keys)
export PATH="$HOME/.local/bin:$PATH" && uv run python -m pytest server/tests/test_llm_client.py::test_execute_success -v

# All tests in a directory
export PATH="$HOME/.local/bin:$PATH" && uv run python -m pytest server/tests/ -v --tb=no
```

## Code Style Guidelines

- Type hints throughout for better IDE support
- Minimal comments - code should be self-documenting
- Custom exception hierarchy for clear error messages
- Pydantic for all data validation
- Thread-safe operations where needed (vault caching)
- Async/await for I/O operations (LLM calls, HTTP)

## Project Structure

```
dakora/                         # Monorepo root
├── server/                     # Platform backend
│   ├── dakora_server/
│   │   ├── main.py            # FastAPI app
│   │   ├── config.py          # Settings and vault singleton
│   │   ├── api/               # API routes
│   │   │   ├── prompts.py
│   │   │   ├── render.py
│   │   │   ├── models.py
│   │   │   ├── health.py
│   │   │   └── schemas.py
│   │   └── core/              # Business logic
│   │       ├── vault.py
│   │       ├── renderer.py
│   │       ├── model.py
│   │       ├── types.py
│   │       ├── exceptions.py
│   │       ├── logging.py
│   │       ├── watcher.py
│   │       ├── registry/      # Template registry
│   │       │   ├── base.py
│   │       │   ├── core.py
│   │       │   ├── backends/
│   │       │   ├── implementations/
│   │       │   └── serialization.py
│   │       └── llm/           # LLM integration
│   │           ├── client.py
│   │           └── models.py
│   ├── tests/                 # Server tests
│   ├── Dockerfile
│   └── pyproject.toml
│
├── packages/                  # Client SDKs
│   └── client-python/
│       ├── dakora_client/
│       │   ├── client.py
│       │   ├── prompts.py
│       │   └── types.py
│       └── pyproject.toml
│
├── cli/                       # CLI tool
│   ├── dakora_cli/
│   │   ├── main.py
│   │   └── templates/
│   └── pyproject.toml
│
├── studio/                    # Web UI
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   ├── pages/
│   │   ├── views/
│   │   ├── hooks/
│   │   └── utils/
│   ├── dist/                  # Built UI (gitignored)
│   ├── Dockerfile
│   ├── nginx.conf
│   └── package.json
│
├── docker/                    # Docker deployment
│   ├── docker-compose.yml
│   └── .env.example
│
├── examples/                  # Usage examples
│   ├── openai-agents/
│   └── microsoft-agent-framework/
│
├── prompts/                   # Example templates
├── promptvault.yaml          # Config file
└── CLAUDE.md                 # This file
```

## Configuration

Projects use `promptvault.yaml` config files:

```yaml
registry: local
prompt_dir: ./prompts
logging:
  enabled: true
  backend: sqlite
  db_path: ./dakora.db
```

**Configuration Options:**
- `registry` - Registry type (local or azure)
- `prompt_dir` - Path to templates directory (local registry)
- `logging.enabled` - Enable execution logging
- `logging.backend` - Logging backend (sqlite)
- `logging.db_path` - SQLite database path

## Publishing

Three separate packages are published:

1. **dakora** (CLI) - PyPI
   - Minimal dependencies (typer only)
   - Commands for managing platform

2. **dakora-client** (Python SDK) - PyPI
   - Dependencies: httpx, pydantic
   - Full API client library

3. **dakora-server** (Server) - Not published
   - Docker-only deployment
   - Contains all backend logic

## CI/CD

GitHub Actions workflows:
- `.github/workflows/ci.yml` - Tests and validation
- `.github/workflows/release-cli.yml` - Publish CLI to PyPI
- `.github/workflows/release-client-python.yml` - Publish client to PyPI
- `.github/workflows/release-docker.yml` - Build and push Docker images

## Future Enhancements

**Planned:**
- TypeScript SDK (`@dakora/client`)
- Go SDK (`dakora-go`)
- Cloud hosting platform
- Team collaboration features
- Advanced caching strategies
- More storage backends (S3, GCS)