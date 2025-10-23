# Contributing to Dakora

Thank you for your interest in contributing to Dakora! This guide will help you get started.

## Table of Contents

- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Running the Platform](#running-the-platform)
- [Testing](#testing)
- [Code Style](#code-style)
- [Database Migrations](#database-migrations)
- [Submitting Changes](#submitting-changes)

## Development Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker and Docker Compose
- [uv](https://github.com/astral-sh/uv) package manager

### Initial Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/dakora.git
   cd dakora
   ```

2. Set up Python environment:
   ```bash
   export PATH="$HOME/.local/bin:$PATH"
   uv sync
   ```

3. Configure environment variables:
   ```bash
   cp docker/.env.example .env
   # Edit .env and add your API keys (OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.)
   ```

4. Start the platform:
   ```bash
   dakora start
   ```

## Project Structure

Dakora is a monorepo with the following packages:

- **`server/`** - FastAPI backend with REST API, authentication, and multi-tenancy
- **`packages/client-python/`** - Python SDK for interacting with the API
- **`cli/`** - Command-line tool for managing the platform
- **`studio/`** - React-based web UI for template development
- **`docker/`** - Docker Compose configuration for local deployment

See [CLAUDE.md](./CLAUDE.md) for detailed architecture documentation.

## Running the Platform

### Using Docker (Recommended)

```bash
# Start all services
dakora start

# Stop all services
dakora stop

# View logs
docker-compose -f docker/docker-compose.yml logs -f
```

The platform will be available at:
- Studio UI: http://localhost:3000
- API: http://localhost:54321

### Development Mode (Server Only)

For faster iteration when working on the server:

```bash
cd server
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/dakora"
export PATH="$HOME/.local/bin:$PATH"
uv run uvicorn dakora_server.main:app --reload --port 8000
```

### Studio Development

For UI development with hot reload:

```bash
cd studio
npm install
npm run dev
```

## Testing

### Running Tests

```bash
# Run all tests
export PATH="$HOME/.local/bin:$PATH"
uv run python -m pytest

# Run specific test categories
export PATH="$HOME/.local/bin:$PATH"
uv run python server/tests/test_runner.py unit
export PATH="$HOME/.local/bin:$PATH"
uv run python server/tests/test_runner.py integration
export PATH="$HOME/.local/bin:$PATH"
uv run python server/tests/test_runner.py performance

# Run specific test file
export PATH="$HOME/.local/bin:$PATH"
uv run python -m pytest server/tests/test_vault_execute.py -v
```

### Writing Tests

- Place tests in `server/tests/`
- Use pytest fixtures from `conftest.py`
- Follow existing test patterns (unit, integration, performance)
- Tests requiring LLM API keys should be marked appropriately

## Code Style

### Python

- **Type hints**: Always use type hints for parameters and return values
- **Async/await**: Use for I/O operations (LLM calls, HTTP, database)
- **Pydantic models**: Use Pydantic v2 for data validation
- **Docstrings**: Use Google-style docstrings
- **Imports**: Group as standard library, third-party, local
- **Error handling**: Use `HTTPException` for API errors; custom exceptions (`DakoraError`, `TemplateNotFound`, etc.) for business logic
- **Formatting**: Run Black with repo configuration:
  ```bash
  black server/ packages/ cli/
  ```
- **Type checking**: Keep Pylance/mypy diagnostics clean

### TypeScript/React

- Use TypeScript for all new code
- Follow existing component patterns in `studio/src/`
- Use shadcn/ui components when possible
- Keep components focused and reusable

## Database Migrations

Dakora uses Alembic for database migrations:

### Creating a Migration

```bash
cd server
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/dakora"
export PATH="$HOME/.local/bin:$PATH"
uv run alembic revision -m "Description of change"
```

Edit the generated file in `server/alembic/versions/` and implement `upgrade()` and `downgrade()` functions.

### Running Migrations

```bash
# Upgrade to latest
export PATH="$HOME/.local/bin:$PATH"
uv run alembic upgrade head

# Rollback one version
export PATH="$HOME/.local/bin:$PATH"
uv run alembic downgrade -1

# Check current version
export PATH="$HOME/.local/bin:$PATH"
uv run alembic current
```

### Migration Best Practices

- Test locally before pushing
- Write `downgrade()` logic for safe rollbacks
- Keep migrations small and focused
- Use SQLAlchemy Core (not ORM)
- Never skip migrations

## Submitting Changes

### Pull Request Process

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**:
   - Write clear, focused commits
   - Include tests for new functionality
   - Update documentation as needed

3. **Test your changes**:
   ```bash
   # Run tests
   export PATH="$HOME/.local/bin:$PATH"
   uv run python -m pytest

   # Format code
   black server/ packages/ cli/

   # Test migrations (if applicable)
   export PATH="$HOME/.local/bin:$PATH"
   uv run alembic upgrade head
   ```

4. **Push and create PR**:
   ```bash
   git push -u origin feature/your-feature-name
   ```

   Then create a pull request on GitHub targeting the `main` branch.

### PR Guidelines

- Fill out the PR template completely
- Ensure all CI checks pass
- Link related issues
- Request review from maintainers
- Address review feedback promptly

### Commit Messages

Use clear, descriptive commit messages:

```
feat: add template comparison endpoint
fix: resolve race condition in vault caching
docs: update API key configuration guide
test: add integration tests for prompt manager
```

Prefixes: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `ci`

## Getting Help

- **Documentation**: See [CLAUDE.md](./CLAUDE.md) for architecture details
- **Issues**: Check existing [GitHub Issues](https://github.com/yourusername/dakora/issues)
- **Discussions**: Join [GitHub Discussions](https://github.com/yourusername/dakora/discussions)

## Code of Conduct

- Be respectful and inclusive
- Welcome newcomers
- Focus on constructive feedback
- Follow project guidelines

Thank you for contributing to Dakora! 