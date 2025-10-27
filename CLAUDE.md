# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Overview

Dakora is a **multi-tenant SaaS platform** for managing prompt templates with versioning and LLM execution. Monorepo with:

- **Server** (`server/`): FastAPI backend with REST API, auth, multi-tenancy
- **Client SDK** (`packages/client-python/`): Python client library
- **CLI** (`cli/`): Command-line tool
- **Studio** (`studio/`): React web UI (see [UI Development Guide](assets/ui-development-guide.md))
- **Docker** (`docker/`): Local deployment

**Key Principles:**
- **Multi-tenancy**: Workspaces → Projects → Prompts
- **Auth**: Clerk JWT, API keys (hashed), or no-auth mode
- **Storage**: Two-layer (DB metadata + Azure Blob YAML content)
- **Database**: PostgreSQL with SQLAlchemy Core (no ORM), Alembic migrations

## Key Files & Locations

### Server (`server/dakora_server/`)

**Entry & Config:**
- `main.py` - FastAPI app, CORS, routes, static files
- `config.py` - Pydantic settings, environment variables
- `auth.py` - Auth context extraction, project access validation

**API Routes (`api/`):**
- `project_prompts.py`, `project_parts.py`, `project_executions.py`, `project_optimizations.py` - Project-scoped APIs
- `api_keys.py`, `me.py`, `webhooks.py`, `health.py`, `schemas.py`

**Core Logic (`core/`):**
- **Storage**: `prompt_manager.py` (DB+blob sync), `part_manager.py`, `vault.py` (storage abstraction), `provisioning.py`
- **Templates**: `model.py` (TemplateSpec, InputSpec), `renderer.py` (Jinja2)
- **Registry**: `registry/` (local/Azure backends, YAML serialization)
- **API Keys**: `api_keys/` (service, generator, validator - 10 keys/project limit)
- **Optimizer**: `optimizer/` (engine, generator, evaluator, explainer, quota)
- **LLM**: `llm/` (provider base, registry, Azure OpenAI, Google Gemini)
- **Database**: `database.py` (SQLAlchemy Core, table defs), `logging.py` (execution logging)
- **Utilities**: `exceptions.py`, `types.py`, `watcher.py`, `part_loader.py`

**Migrations**: `alembic/` - Database migrations (see Database section)

### Studio (`studio/src/`)

See [UI Development Guide](assets/ui-development-guide.md) for details. Key locations:
- `App.tsx` - Router, `components/` - UI, `pages/` - Pages, `hooks/useApi.ts`, `utils/api.ts`

### Client SDK & CLI

- `packages/client-python/` - Python SDK (dakora-client on PyPI)
- `cli/` - CLI tool (dakora on PyPI)

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

## Database & Migrations

**Alembic** (SQLAlchemy Core, PostgreSQL). Migrations run automatically in Docker and on deploy.

**Key Commands:**
```bash
# Create migration
cd server && export PATH="$HOME/.local/bin:$PATH" && uv run alembic revision -m "description"
# Run migrations
export PATH="$HOME/.local/bin:$PATH" && uv run alembic upgrade head
# Check status
export PATH="$HOME/.local/bin:$PATH" && uv run alembic current
```

**Core Tables:**
- `users`, `workspaces`, `workspace_members`, `workspace_quotas`
- `projects`, `prompts`, `prompt_parts`
- `prompt_executions` - Execution metrics (tokens, cost, latency)
- `optimization_runs` - Optimization history
- `api_keys`, `logs`

**Important:**
- Always add new tables to `database.py`
- **Timestamps**: Use `TIMESTAMP WITH TIME ZONE` (timestamptz) with `server_default=text("(NOW() AT TIME ZONE 'UTC')")`. This ensures all timestamps are stored in UTC and automatically handled correctly across timezones. SQLAlchemy type: `DateTime(timezone=True)`
- Use SQLAlchemy Core statements for queries
- Test locally before deploying
- Write downgrade() logic

## Templates

YAML format with Jinja2 syntax:
- Input types: `string`, `number`, `boolean`, `array<string>`, `object`
- Custom filters: `yaml`, `default`
- Stored in Azure Blob or local filesystem

## Features Overview

**Prompt Execution:**
- Multi-provider LLM support (Azure OpenAI, Google Gemini)
- Quota enforcement, token tracking, execution history
- API: `POST /api/projects/{id}/prompts/{id}/execute`

**Prompt Optimization:**
- AI-powered optimizer creates variants, scores, selects best
- Tier-based quotas (free: 10/mo, starter: 50/mo, pro: unlimited)
- API: `POST /api/projects/{id}/prompts/{id}/optimize`

**API Keys:**
- Project-scoped, hashed storage, 10 keys per project limit
- Format: `dk_proj_{project_id}_{random}`

## Testing

**IMPORTANT**: When writing or debugging tests, refer to the comprehensive [Testing Guide](assets/testing-guide.md) for detailed information on:

- Test infrastructure and directory structure
- Factory patterns and fixtures
- Writing integration tests
- Authentication in tests
- Database management
- Best practices and common patterns

### Quick Reference

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

**Key Principles:**

- All integration tests must be marked with `@pytest.mark.integration`
- Use factory functions (`create_test_user`, `create_test_workspace`, `create_test_project`) for test data
- Use FastAPI dependency overrides - never monkey patch
- Always use the `db_connection` fixture - don't create your own database connections
- Use SQLAlchemy Core statements for database queries

## Code Style

**Python:**
- Type hints required
- Async/await for I/O
- Pydantic v2 for validation
- Google-style docstrings
- HTTPException for API errors, DakoraError hierarchy for business logic
- Black formatting (line length 88)
- Clean Pylance diagnostics

**TypeScript/React:**
- See [UI Development Guide](assets/ui-development-guide.md)