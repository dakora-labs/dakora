# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Dakora is a **multi-tenant SaaS platform** for managing prompt templates with type-safe inputs and versioning. The project is organized as a **monorepo** with the following packages:

- **Server** (`server/`): FastAPI-based platform backend with REST API, authentication, and multi-tenancy
- **Client SDK** (`packages/client-python/`): Python client library for interacting with the API
- **CLI** (`cli/`): Minimal command-line tool for managing the platform
- **Studio** (`studio/`): React-based web UI for template development and testing
- **Docker** (`docker/`): Docker Compose configuration for local deployment

**Key Architecture Principles:**

- **Multi-tenancy**: Workspaces, projects, and user-scoped storage
- **Authentication**: Clerk JWT tokens, API keys (hashed), or no-auth mode for development
- **Storage**: Azure Blob Storage for templates, PostgreSQL for metadata and indexes
- **Two-layer architecture**: Database indexes prompt metadata, blob storage holds YAML content

## Architecture

### Server (`server/dakora_server/`)

**Main Entry Point:**

- `main.py` - FastAPI application factory with CORS middleware, API routes, and Studio static file serving

**Configuration:**

- `config.py` - Pydantic settings with environment variables, vault singleton pattern

**Authentication & Authorization (`auth.py`):**

- `get_auth_context()` - Extract auth from headers (API key, JWT, or no-auth mode)
- `validate_project_access()` - Ensure user can access project
- `get_project_vault()` - Get project-scoped vault instance with correct storage prefix
- `get_current_user_id()` - Extract user ID from auth context

**API Routes (`api/`):**

- `project_prompts.py` - Project-scoped prompt CRUD (`/api/projects/{project_id}/prompts/`)
- `project_parts.py` - Reusable prompt parts/snippets (`/api/projects/{project_id}/parts/`)
- `api_keys.py` - API key management (`/api/projects/{project_id}/api-keys/`)
- `me.py` - User context and default project (`/api/me`)
- `webhooks.py` - Clerk webhook handlers for user provisioning
- `health.py` - Health check endpoint
- `schemas.py` - Pydantic request/response models

**Core Business Logic (`core/`):**

**Multi-Tenancy & Storage:**

- `prompt_manager.py` - Two-layer prompt management (DB metadata + blob storage)
- `part_manager.py` - Reusable prompt parts management
- `provisioning.py` - Auto-create workspaces and default projects for new users
- `vault.py` - Storage abstraction with thread-safe caching, supports project-scoped prefixes

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

**API Key System (`core/api_keys/`):**

- `service.py` - APIKeyService for CRUD operations, enforces 10-key-per-project limit
- `generator.py` - Secure key generation (dk_proj_{project_id}_{random_32_chars})
- `validator.py` - Cached validation with 1-minute TTL, checks expiration and revocation
- `models.py` - Pydantic models for API key requests/responses

**Database & Logging:**

- `database.py` - SQLAlchemy Core setup with PostgreSQL connection pooling, table definitions
- `logging.py` - PostgreSQL-based execution logging (migrated from SQLite)
- `types.py` - Type definitions (InputType, etc.)
- `exceptions.py` - Custom exception hierarchy (DakoraError, TemplateNotFound, ValidationError, etc.)
- `watcher.py` - File system monitoring for hot-reload
- `part_loader.py` - Load and parse prompt parts from storage

**Dependencies:**

- FastAPI + Uvicorn - Web framework
- Pydantic - Data validation
- Jinja2 - Template rendering
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
- `types.py` - Data models (TemplateInfo, RenderResult)

**Usage Example:**

```python
from dakora_client import Dakora

# Local (Docker)
dakora = Dakora("http://localhost:54321")
templates = await dakora.prompts.list()
result = await dakora.prompts.render("greeting", {"name": "Alice"})

# Cloud
dakora = Dakora("https://api.dakora.cloud", api_key="dk_xxx")
result = await dakora.prompts.render("greeting", {"name": "Alice"})
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
export PATH="$HOME/.local/bin:$PATH" && uv run python -m pytest server/tests/test_database.py -v

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

Core tables support multi-tenant architecture:

- `users` - User accounts (clerk_user_id, email, name)
- `workspaces` - Workspaces/organizations (slug, name, type: personal/team, owner_id)
- `workspace_members` - Workspace membership (workspace_id, user_id, role)
- `projects` - Projects within workspaces (workspace_id, slug, name, description)
- `prompts` - Prompt metadata index (project_id, prompt_id, version, storage_path, metadata)
- `prompt_parts` - Reusable prompt snippets (project_id, part_id, category, name, content)
- `api_keys` - Project-scoped API keys (user_id, project_id, key_hash, key_prefix, key_suffix, expires_at, revoked_at)
- `logs` - Execution logging (prompt_id, version, inputs_json, output_text, provider, model, tokens, cost, latency)

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

**Key Test Files:**

- `test_registry_azure.py` - Azure storage tests
- `conftest.py` - Pytest fixtures

**Running Specific Tests:**

```bash
# Run all tests
export PATH="$HOME/.local/bin:$PATH" && uv run python -m pytest server/tests/ -v --tb=no
```

## Code Style Guidelines

### Python Code

1. **Type Hints**: Always use type hints for function parameters and return values for better IDE support
2. **Async/Await**: Use async/await patterns for I/O operations (HTTP, database)
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
│   │   ├── main.py            # FastAPI app with routes and middleware
│   │   ├── config.py          # Pydantic settings, Clerk config
│   │   ├── auth.py            # Authentication/authorization
│   │   ├── api/               # API routes
│   │   │   ├── project_prompts.py   # Project-scoped prompt CRUD
│   │   │   ├── project_parts.py     # Reusable prompt parts
│   │   │   ├── api_keys.py          # API key management
│   │   │   ├── me.py                # User context
│   │   │   ├── webhooks.py          # Clerk webhooks
│   │   │   ├── health.py            # Health check
│   │   │   └── schemas.py           # Request/response models
│   │   └── core/              # Business logic
│   │       ├── prompt_manager.py    # Prompt DB + blob sync
│   │       ├── part_manager.py      # Parts management
│   │       ├── part_loader.py       # Part loading from storage
│   │       ├── provisioning.py      # Auto-provision workspaces
│   │       ├── vault.py             # Storage abstraction
│   │       ├── renderer.py          # Jinja2 rendering
│   │       ├── model.py             # Template data models
│   │       ├── database.py          # SQLAlchemy Core
│   │       ├── logging.py           # Execution logging
│   │       ├── exceptions.py        # Custom exceptions
│   │       ├── types.py             # Type definitions
│   │       ├── watcher.py           # File watching
│   │       ├── api_keys/            # API key system
│   │       │   ├── service.py       # CRUD operations
│   │       │   ├── generator.py     # Key generation
│   │       │   ├── validator.py     # Cached validation
│   │       │   └── models.py        # Pydantic models
│   │       └── registry/            # Template registry
│   │           ├── base.py          # Protocol
│   │           ├── core.py          # TemplateRegistry
│   │           ├── backends/        # Storage backends
│   │           ├── implementations/ # Registry implementations
│   │           └── serialization.py # YAML utils
│   ├── alembic/               # Database migrations
│   │   ├── versions/          # Migration files
│   │   ├── env.py             # Alembic environment
│   │   └── script.py.mako     # Migration template
│   ├── tests/                 # Server tests
│   ├── Dockerfile             # Production image
│   ├── entrypoint.sh          # Runs migrations + starts server
│   └── pyproject.toml
│
├── packages/                  # Client SDKs
│   └── client-python/
│       ├── dakora_client/
│       │   ├── client.py      # Main Dakora class
│       │   ├── prompts.py     # PromptsAPI
│       │   └── types.py       # Data models
│       ├── Makefile           # Build/publish commands
│       └── pyproject.toml
│
├── cli/                       # CLI tool
│   ├── dakora_cli/
│   │   ├── main.py            # Commands (start, stop, init)
│   │   └── templates/         # Embedded templates
│   └── pyproject.toml
│
├── studio/                    # Web UI
│   ├── src/
│   │   ├── App.tsx            # Main app with routing
│   │   ├── components/        # UI components
│   │   ├── pages/             # Page components
│   │   ├── views/             # View components
│   │   ├── hooks/             # Custom hooks
│   │   └── utils/             # Utilities
│   ├── dist/                  # Built UI (gitignored)
│   ├── Dockerfile             # Nginx image
│   ├── nginx.conf             # Nginx configuration
│   └── package.json
│
├── docker/                    # Docker deployment
│   ├── docker-compose.yml     # Local development
│   └── .env.example           # Environment template
│
├── examples/                  # Usage examples
├── prompts/                   # Example templates
├── render.yaml                # Render deployment config
└── CLAUDE.md                  # This file
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
