
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Dakora is a Python library for managing and rendering prompt templates with type-safe inputs, versioning, and optional logging. The architecture consists of:

- **Vault**: Main public API (`dakora/vault.py`) - loads templates, handles caching with thread-safe RLock, and provides TemplateHandle objects
- **Registry**: Template discovery system (`dakora/registry/`) - abstract base with LocalRegistry implementation that scans YAML files in prompt directories
- **Model**: Pydantic-based template specifications (`dakora/model.py`) - defines TemplateSpec with input validation and type coercion
- **Renderer**: Jinja2-based template rendering (`dakora/renderer.py`) - includes custom filters like `yaml` and `default`
- **CLI**: Typer-based command interface (`dakora/cli.py`) - provides init, list, get, bump, watch, and playground commands
- **Playground**: FastAPI-based web server (`dakora/playground.py`) - interactive React-based web interface for template development and testing, with demo mode support
- **Logging**: Optional SQLite-based execution logging (`dakora/logging.py`) - tracks template executions with inputs, outputs, and metadata
- **Watcher**: File system monitoring (`dakora/watcher.py`) - hot-reload support for template changes during development
- **Exceptions**: Custom exception hierarchy (`dakora/exceptions.py`) - DakoraError, TemplateNotFoundError, RegistryError, etc.

Templates are stored as YAML files with structure: `{id, version, description, template, inputs, metadata}`. The `inputs` field defines typed parameters (string, number, boolean, array<string>, object) with validation and defaults.

The playground UI is built with React, TypeScript, and shadcn/ui components, providing a modern interface for template development. It supports both development mode (hot-reload) and demo mode (read-only with example templates).

## Development Commands

**Environment Setup:**
```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies
export PATH="$HOME/.local/bin:$PATH" && uv sync

# Run CLI commands during development
export PATH="$HOME/.local/bin:$PATH" && uv run python -m dakora.cli --help
```

**Testing the CLI:**
```bash
# Initialize a test project
export PATH="$HOME/.local/bin:$PATH" && uv run python -m dakora.cli init

# List templates
export PATH="$HOME/.local/bin:$PATH" && uv run python -m dakora.cli list

# Get template content
export PATH="$HOME/.local/bin:$PATH" && uv run python -m dakora.cli get summarizer

# Watch for changes
export PATH="$HOME/.local/bin:$PATH" && uv run python -m dakora.cli watch
```

**Testing the Playground:**
```bash
# Start interactive playground web interface
export PATH="$HOME/.local/bin:$PATH" && uv run python -m dakora.cli playground --port 3000

# Start in development mode with auto-reload
export PATH="$HOME/.local/bin:$PATH" && uv run python -m dakora.cli playground --dev

# Start in demo mode (read-only with example templates)
export PATH="$HOME/.local/bin:$PATH" && uv run python -m dakora.cli playground --demo

# Skip UI build (use existing build)
export PATH="$HOME/.local/bin:$PATH" && uv run python -m dakora.cli playground --no-build

# Don't open browser automatically
export PATH="$HOME/.local/bin:$PATH" && uv run python -m dakora.cli playground --no-browser
```

**Library Usage:**
```bash
# Test vault functionality
export PATH="$HOME/.local/bin:$PATH" && uv run python -c "
from dakora.vault import Vault
v = Vault(prompt_dir='./prompts')
tmpl = v.get('summarizer')
print(tmpl.render(input_text='test'))
"
```

**Running Tests:**
```bash
# Run all tests
export PATH="$HOME/.local/bin:$PATH" && uv run python -m pytest

# Run specific test categories
export PATH="$HOME/.local/bin:$PATH" && uv run python tests/test_runner.py unit
export PATH="$HOME/.local/bin:$PATH" && uv run python tests/test_runner.py integration
export PATH="$HOME/.local/bin:$PATH" && uv run python tests/test_runner.py performance

# Quick validation test
python validate_tests.py

# Run tests with coverage
export PATH="$HOME/.local/bin:$PATH" && uv run python -m pytest --cov=dakora
```

## Key Architecture Notes

- Thread-safe caching in Vault class using RLock for concurrent access
- Registry pattern allows future extension beyond local filesystem (e.g., remote registries)
- TemplateHandle separates template metadata from rendering concerns
- Input validation happens at render time via Pydantic with custom type coercion
- Jinja2 environment configured with StrictUndefined to catch template errors early
- File watching uses separate Watcher class for hot-reload functionality
- Playground uses FastAPI for backend with CORS support and static file serving
- UI build process managed by NodeJS/npm, with automatic build on first run
- Demo mode serves example templates from embedded YAML files, read-only interface
- Logging backend stores executions with timestamps, inputs, outputs, and latency metrics

## Configuration

Projects use `dakora.yaml` config files with structure:
```yaml
registry: "local"
prompt_dir: "./prompts"
logging:
  enabled: true
  backend: "sqlite"
  db_path: "./dakora.db"
```

## Code Style Guidelines

- **No emoticons**: Never use emoticons or emojis in code, commit messages, or any generated content
- **Minimal comments**: Avoid code comments unless absolutely necessary for complex logic or non-obvious behavior
- **Assume expertise**: Write code assuming prior software engineering knowledge - avoid explanatory comments for standard patterns
- **Type hints**: Use Python type hints throughout the codebase for better IDE support
- **Error handling**: Use custom exception hierarchy for clear error messages
- **Testing**: Maintain test coverage with unit, integration, and performance tests

## Project Structure

```
dakora/
├── dakora/
│   ├── __init__.py          # Public API exports
│   ├── vault.py             # Main Vault class
│   ├── model.py             # Pydantic models for templates
│   ├── renderer.py          # Jinja2 rendering engine
│   ├── cli.py               # Typer-based CLI
│   ├── playground.py        # FastAPI web server
│   ├── logging.py           # SQLite logging backend
│   ├── watcher.py           # File system monitoring
│   ├── exceptions.py        # Custom exception hierarchy
│   └── registry/
│       ├── base.py          # Abstract registry interface
│       └── local.py         # Local filesystem registry
├── playground-ui/           # React + TypeScript UI
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── lib/             # Utilities and API client
│   │   └── App.tsx          # Main application
│   └── package.json
├── tests/                   # Test suite
├── prompts/                 # Example templates
└── pyproject.toml           # Project metadata