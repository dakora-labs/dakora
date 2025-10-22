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

**Database & Logging:**

- `database.py` - SQLAlchemy Core setup with PostgreSQL connection pooling, table definitions
- `logging.py` - PostgreSQL-based execution logging (migrated from SQLite)
- `types.py` - Type definitions (InputType, etc.)
- `exceptions.py` - Custom exception hierarchy (DakoraError, TemplateNotFound, ValidationError, etc.)
- `watcher.py` - File system monitoring for hot-reload

**Dependencies:**

- FastAPI + Uvicorn - Web framework
- Pydantic - Data validation
- Jinja2 - Template rendering
- litellm - Multi-provider LLM integration
- PyYAML - Template storage format
- Watchdog - File system monitoring
- SQLAlchemy - Database toolkit (Core only, no ORM)
- Alembic - Database migration tool
- psycopg2-binary - PostgreSQL adapter
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

```text
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

### Database Migrations

Dakora uses **Alembic** for database migrations with **SQLAlchemy Core** (not ORM) and **PostgreSQL**.

**Architecture:**

- **Local (Docker Compose)**: PostgreSQL 15 container
- **Production (Render)**: Supabase (PostgreSQL-compatible)
- **Migration System**: Alembic with environment-aware DATABASE_URL

**Key Files:**

- `server/dakora_server/core/database.py` - SQLAlchemy Core setup, table definitions, connection pooling
- `server/dakora_server/core/logging.py` - Logger using PostgreSQL (replaced SQLite)
- `server/alembic/` - Migration scripts directory
- `server/alembic.ini` - Alembic configuration
- `server/alembic/env.py` - Environment configuration (reads DATABASE_URL)
- `server/entrypoint.sh` - Docker entrypoint with migration automation

**How Migrations Work:**

**Docker Compose (Local):**

1. `docker-compose up` starts PostgreSQL with healthcheck
2. API container waits for DB to be healthy
3. `entrypoint.sh` runs `alembic upgrade head` automatically
4. Server starts after migrations complete

**Render (Production):**

1. Push code to GitHub
2. Render triggers deployment
3. **Pre-deploy command** runs: `alembic upgrade head`
4. New service version deploys only after successful migration
5. Zero downtime, safe rollouts

**Creating Migrations:**

```bash
# Create new migration
cd server
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/dakora"
export PATH="$HOME/.local/bin:$PATH" && uv run alembic revision -m "Add users table"

# Edit migration file in server/alembic/versions/
# Add upgrade() and downgrade() logic using SQLAlchemy Core

# Run migration
export PATH="$HOME/.local/bin:$PATH" && uv run alembic upgrade head

# Check current version
export PATH="$HOME/.local/bin:$PATH" && uv run alembic current

# Rollback one version
export PATH="$HOME/.local/bin:$PATH" && uv run alembic downgrade -1
```

**Migration Best Practices:**

- **Always test locally** before deploying to production
- **Write downgrade()** logic for safe rollbacks
- **Keep migrations small** and focused on single changes
- **Never skip migrations** - they run automatically
- **Test with empty DB** to ensure idempotency

**Current Schema:**

- `logs` table - Execution logging (prompt_id, version, inputs_json, output_text, provider, model, tokens, cost, latency)

**Supabase Setup (Production):**

1. Create [Supabase](https://supabase.com) project
2. Get connection string from project settings (Database → Connection String → URI)
3. Add to Render environment variables:

    ```text
    DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres
    ```

4. Migrations run automatically via `preDeployCommand` in render.yaml

**Troubleshooting:**

```bash
# Test database connection
python -c "from dakora_server.core.database import create_db_engine, wait_for_db; \
engine = create_db_engine(); print('Connected!' if wait_for_db(engine) else 'Failed')"

# Check migration status
cd server && export PATH="$HOME/.local/bin:$PATH" && uv run alembic current

# View migration history
cd server && export PATH="$HOME/.local/bin:$PATH" && uv run alembic history --verbose

# Force migration (if stuck)
cd server && export PATH="$HOME/.local/bin:$PATH" && uv run alembic stamp head
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

### Python Code

1. **Type Hints**: Always use type hints for function parameters and return values for better IDE support
2. **Async/Await**: Use async/await patterns for I/O operations (LLM calls, HTTP, database)
3. **Pydantic Models**: Use Pydantic v2 models for data validation and settings
4. **Docstrings**: Use Google-style docstrings for functions and classes
5. **Imports**: Group imports (standard library, third-party, local)
6. **Error Handling**: Use FastAPI's HTTPException for API errors; custom exception hierarchy (DakoraError, TemplateNotFound, ValidationError) for business logic
7. **Configuration**: Use Pydantic Settings for environment-based config
8. **Thread Safety**: Implement thread-safe operations where needed (e.g., vault caching with RLock)
9. **Code Clarity**: Write self-documenting code with clear naming; minimize inline comments
10. **Formatting**: Format Python code with Black using the repo `pyproject.toml` configuration (line length 88, Python 3.11 targets)
11. **Static Analysis**: Keep Pylance diagnostics clean—resolve missing type hints, `Any` leaks, and other warnings surfaced by Pylance-equivalent type checkers

## Project Structure

```text
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
