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

Dakora uses a **layered fixture system** with factory patterns for clean, composable integration tests. This approach avoids monkey patching, uses stable UUIDs, and makes it easy to write new tests without fighting with authentication or database setup.

### Test Infrastructure

**Directory Structure:**

```text
server/tests/
├── conftest.py              # Main fixture registration + legacy fixtures
├── factories/               # Data factories for consistent test entities
│   ├── __init__.py
│   ├── constants.py        # Stable UUIDs (TEST_USER_ID, TEST_PROJECT_ID, etc.)
│   ├── users.py            # create_test_user()
│   ├── workspaces.py       # create_test_workspace()
│   └── projects.py         # create_test_project()
├── fixtures/                # Pytest fixtures
│   ├── __init__.py
│   ├── database.py         # db_engine, db_connection
│   ├── auth.py             # auth_context, override_auth_dependencies
│   └── entities.py         # test_user, test_workspace, test_project
├── integration/            # Integration tests
└── unit/                   # Unit tests
```

### Core Principles

1. **Factory Pattern**: Functions create entities with stable, reproducible UUIDs
2. **FastAPI Dependency Overrides**: NEVER monkey patch - use `app.dependency_overrides`
3. **Composable Fixtures**: `test_project` → `test_workspace` → `test_user`
4. **Session-Scoped Fixtures**: Share user/workspace/project across tests for speed
5. **Auto-Cleanup**: `cleanup_project_data` fixture removes test data after each test

### Test Categories & Markers

Dakora uses **pytest markers** to categorize tests and optimize CI runtime:

**Test Categories:**

- **Unit Tests** - Fast, isolated tests with no database or API calls (default, no marker needed)
- **Integration Tests** - Tests that use database, FastAPI TestClient, or dependency overrides (marked with `@pytest.mark.integration`)
- **Performance Tests** - Slow tests for benchmarking (marked with `@pytest.mark.performance`)

**When to Mark as Integration:**

Mark tests with `@pytest.mark.integration` if they:
- Use the database (`db_connection`, `test_engine`, or any database fixture)
- Use FastAPI `TestClient` to call API endpoints
- Use `app.dependency_overrides` to mock dependencies
- Hit external services or require Docker containers

**Example:**

```python
import pytest
from fastapi.testclient import TestClient

@pytest.mark.integration
def test_create_prompt(test_project, test_client, override_auth_dependencies):
    """Integration test that hits the database and API"""
    project_id, _, _ = test_project
    response = test_client.post(f"/api/projects/{project_id}/prompts/", json={...})
    assert response.status_code == 201

@pytest.mark.integration
class TestAPIKeyEndpoints:
    """All tests in this class are integration tests"""

    def test_create_api_key(self, test_client):
        # Uses TestClient and database
        pass
```

**CI Strategy:**

The CI runs different test categories strategically to optimize runtime:

- **Unit tests**: Run on Python 3.11 and 3.12 (fast, comprehensive)
- **Integration tests**: Run on Python 3.11 only (slower, database required)
- **Coverage**: Runs all tests together for comprehensive coverage report

This approach balances thorough testing with CI speed.

**Running Tests Locally:**

```bash
# Run all tests (unit + integration)
export PATH="$HOME/.local/bin:$PATH" && uv run python -m pytest

# Run only unit tests (fast - excludes integration & performance)
export PATH="$HOME/.local/bin:$PATH" && uv run python server/tests/test_runner.py unit -v

# Run only integration tests (requires database)
export PATH="$HOME/.local/bin:$PATH" && uv run python server/tests/test_runner.py integration -v

# Run smoke tests (quick validation)
export PATH="$HOME/.local/bin:$PATH" && uv run python server/tests/test_runner.py smoke -v

# Run specific test file
export PATH="$HOME/.local/bin:$PATH" && uv run python -m pytest server/tests/test_database.py -v
```

### Writing Integration Tests

**IMPORTANT**: All integration tests MUST be marked with `@pytest.mark.integration` so CI can run them properly.

**Basic Pattern (Recommended):**

```python
import pytest

@pytest.mark.integration
def test_create_prompt(test_project, test_client, override_auth_dependencies):
    """Test creating a prompt via API.

    - test_project: Provides (project_id, workspace_id, owner_id)
    - test_client: FastAPI TestClient
    - override_auth_dependencies: Mocks auth to use test_project's owner
    """
    project_id, _, _ = test_project

    response = test_client.post(
        f"/api/projects/{project_id}/prompts/",
        json={
            "prompt_id": "test-prompt",
            "version": "1.0.0",
            "template": "Hello {{ name }}",
            "inputs": {"name": {"type": "string", "required": True}},
        },
    )

    assert response.status_code == 201
```

**Custom Test Data:**

```python
def test_with_multiple_projects(db_connection):
    """Create custom test entities using factories."""
    from tests.factories import create_test_project

    # Create two projects with stable, predictable IDs
    proj1_id, ws1_id, owner1_id = create_test_project(db_connection, suffix="1")
    proj2_id, ws2_id, owner2_id = create_test_project(db_connection, suffix="2")

    # Test logic here
    assert proj1_id != proj2_id
```

**Custom Auth Context:**

```python
def test_unauthorized_access(db_connection, test_client):
    """Test access control with a different user."""
    from tests.factories import create_test_user, create_test_project
    from tests.fixtures.auth import create_custom_auth_override
    from dakora_server.main import app

    # Create project as one user
    project_id, _, owner_id = create_test_project(db_connection, suffix="owner")

    # Create different user who shouldn't have access
    intruder_id = create_test_user(db_connection, suffix="intruder")

    # Override auth to be the intruder
    override = create_custom_auth_override(intruder_id, project_id)
    app.dependency_overrides.update(override)

    # Test that access is denied
    response = test_client.get(f"/api/projects/{project_id}/prompts/")
    assert response.status_code == 403

    app.dependency_overrides.clear()
```

### Factory Functions

**Available Factories:**

```python
from tests.factories import (
    create_test_user,
    create_test_workspace,
    create_test_project,
    TEST_USER_ID,          # Stable default UUIDs
    TEST_WORKSPACE_ID,
    TEST_PROJECT_ID,
)

# Create with defaults
user_id = create_test_user(db_connection)

# Create with custom values
user_id = create_test_user(
    db_connection,
    email="custom@example.com",
    name="Custom User",
)

# Create multiple with suffixes (generates stable UUIDs)
user1_id = create_test_user(db_connection, suffix="1")
user2_id = create_test_user(db_connection, suffix="2")

# Factories are idempotent - calling twice with same ID is safe
user_id = create_test_user(db_connection)  # Creates user
user_id = create_test_user(db_connection)  # Returns existing user
```

**Workspace Factory:**

```python
# Auto-creates owner
workspace_id, owner_id = create_test_workspace(db_connection)

# Use existing owner
user_id = create_test_user(db_connection)
workspace_id, _ = create_test_workspace(
    db_connection,
    owner_id=user_id,
    create_owner=False,
)
```

**Project Factory:**

```python
# Auto-creates workspace and owner
project_id, workspace_id, owner_id = create_test_project(db_connection)

# Use existing workspace
workspace_id, owner_id = create_test_workspace(db_connection)
project_id, _, _ = create_test_project(
    db_connection,
    workspace_id=workspace_id,
    create_workspace=False,
)

# Multiple projects in same workspace
workspace_id, owner_id = create_test_workspace(db_connection)
proj1_id, _, _ = create_test_project(db_connection, workspace_id=workspace_id, suffix="1")
proj2_id, _, _ = create_test_project(db_connection, workspace_id=workspace_id, suffix="2")
```

### Available Fixtures

**Database Fixtures:**

- `db_engine` (session-scoped) - Shared database engine
- `db_connection` (function-scoped) - Fresh connection per test, auto-commit/rollback

**Auth Fixtures:**

- `auth_context` - TestAuthContext with user/workspace/project from test_project
- `override_auth_dependencies` - Overrides FastAPI auth with test_project's owner

**Entity Fixtures:**

- `test_user` (session-scoped) - Default test user
- `test_workspace` (session-scoped) - Default test workspace
- `test_project` (session-scoped) - Default test project

**Client Fixture:**

- `test_client` - FastAPI TestClient for API testing

### Authentication in Tests

**Never Monkey Patch Authentication**

Use FastAPI's dependency override system:

```python
# ✅ CORRECT: Use dependency overrides
def test_with_auth(test_client, override_auth_dependencies):
    response = test_client.get("/api/projects/...")
    assert response.status_code == 200

# ❌ WRONG: Monkey patching
def test_with_monkey_patch(monkeypatch):
    monkeypatch.setattr("dakora_server.auth.get_auth_context", ...)
```

**Why Dependency Overrides?**

- Clean, explicit, and supported by FastAPI
- No side effects or test pollution
- Auto-cleanup when fixture completes
- Type-safe and testable

### Database Management

**Session-Scoped Data:**

Tests share user/workspace/project fixtures across the entire test session for speed. Each test's changes are cleaned up automatically by `cleanup_project_data`.

**Cleanup Strategy:**

- `cleanup_project_data` (autouse) - Removes prompts/parts/keys after each test
- Session fixtures clean up on session teardown
- No full DB resets between tests (fast!)

### Running Tests

```bash
# Run all tests
export PATH="$HOME/.local/bin:$PATH" && uv run python -m pytest server/tests/ -v

# Run specific test file
export PATH="$HOME/.local/bin:$PATH" && uv run python -m pytest server/tests/integration/test_prompts_api.py -v

# Run specific test function
export PATH="$HOME/.local/bin:$PATH" && uv run python -m pytest server/tests/integration/test_prompts_api.py::test_create_prompt -v

# Run with output (useful for debugging)
export PATH="$HOME/.local/bin:$PATH" && uv run python -m pytest server/tests/ -v -s

# Run without traceback (cleaner output)
export PATH="$HOME/.local/bin:$PATH" && uv run python -m pytest server/tests/ -v --tb=no
```

### Best Practices

1. **Use Factories for Test Data**: Don't create users/projects manually, use factories
2. **Request Only What You Need**: If you only need a user, request `test_user`, not `test_project`
3. **Use Suffixes for Multiple Entities**: `create_test_user(conn, suffix="1")` for stable IDs
4. **Clean Up in Tests**: If you create extra data, clean it up (or rely on auto-cleanup)
5. **Use Dependency Overrides**: Never monkey patch FastAPI dependencies
6. **Keep Tests Fast**: Share session fixtures, avoid unnecessary DB writes
7. **Write Descriptive Docstrings**: Explain what fixtures are used and why

### Common Patterns

**Test Multiple Projects:**

```python
def test_project_isolation(db_connection, test_client):
    from tests.factories import create_test_project
    from tests.fixtures.auth import create_custom_auth_override
    from dakora_server.main import app

    # Create two projects with separate owners
    proj1_id, _, owner1_id = create_test_project(db_connection, suffix="1")
    proj2_id, _, owner2_id = create_test_project(db_connection, suffix="2")

    # Create prompt in project 1
    override = create_custom_auth_override(owner1_id, proj1_id)
    app.dependency_overrides.update(override)

    test_client.post(f"/api/projects/{proj1_id}/prompts/", json={...})

    # Verify project 2 doesn't see it
    override = create_custom_auth_override(owner2_id, proj2_id)
    app.dependency_overrides.update(override)

    response = test_client.get(f"/api/projects/{proj2_id}/prompts/")
    assert len(response.json()) == 0

    app.dependency_overrides.clear()
```

**Test Quotas:**

```python
def test_quota_enforcement(db_connection, test_client):
    from tests.factories import create_test_project
    from dakora_server.core.database import workspace_quotas_table
    from sqlalchemy import insert
    from datetime import datetime, timedelta, timezone

    project_id, workspace_id, owner_id = create_test_project(db_connection, suffix="quota")

    # Create quota
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    db_connection.execute(
        insert(workspace_quotas_table).values(
            workspace_id=workspace_id,
            tier="free",
            tokens_used_month=99_900,
            tokens_limit_month=100_000,
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
        )
    )
    db_connection.commit()

    # Test that quota is enforced
    # ... test logic
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
- always add the table for alechemy core to database.py as well. Use utc timestamps - no timezone
- for db queries use queries with SQLAlchemy Core statements
- add to CLAUDE.md that features and integration tests should look the reuse db connection via db_connection method. Dont create your own