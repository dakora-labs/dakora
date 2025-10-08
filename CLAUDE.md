
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Dakora is a Python library for managing and rendering prompt templates with type-safe inputs, versioning, and optional logging. The architecture consists of:

- **Vault**: Main public API (`dakora/vault.py`) - loads templates, handles caching with thread-safe RLock, and provides TemplateHandle objects
- **Registry**: Template discovery system (`dakora/registry/`) - abstract base with LocalRegistry implementation that scans YAML files in prompt directories
- **Model**: Pydantic-based template specifications (`dakora/model.py`) - defines TemplateSpec with input validation and type coercion
- **Renderer**: Jinja2-based template rendering (`dakora/renderer.py`) - includes custom filters like `yaml` and `default`
- **CLI**: Typer-based command interface (`dakora/cli.py`) - provides init, list, get, bump, watch, config, and playground commands
- **Playground**: FastAPI-based web server (`dakora/playground.py`) - interactive React-based web interface for template development and testing, with demo mode support
- **Logging**: Optional SQLite-based execution logging (`dakora/logging.py`) - tracks template executions with inputs, outputs, and metadata
- **Watcher**: File system monitoring (`dakora/watcher.py`) - hot-reload support for template changes during development
- **Exceptions**: Custom exception hierarchy (`dakora/exceptions.py`) - DakoraError, TemplateNotFoundError, RegistryError, etc.

Templates are stored as YAML files with structure: `{id, version, description, template, inputs, metadata}`. The `inputs` field defines typed parameters (string, number, boolean, array<string>, object) with validation and defaults.

The playground UI is built with React, TypeScript, and shadcn/ui components, providing a modern interface for template development. It supports both development mode (hot-reload) and demo mode (read-only with example templates).

## Working with API Keys

Dakora integrates with LLM providers for examples and playground functionality. API keys are managed through environment variables.
**Setup:**
1. Create `.env` file in project root (already in `.gitignore`)
2. Add required API keys:
```
OPENAI_API_KEY="example_key_openai_123"
```
3. Validate configuration: `uv run python -m dakora.cli config`

**The `config` Command:**
- Validates API key presence and format
- Usage: `dakora config [--provider PROVIDER]`
- Returns `✓ {key} found` on success and `✗ {key} not set` for missing keys
- Exits with `0` on success, and `1` if a specific key is not found or a provider is not supported

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

**API Key Configuration:**
```bash
# Create .env file for API keys
touch .env

# Validate API key configuration
export PATH="$HOME/.local/bin:$PATH" && uv run python -m dakora.cli config check

# Check specific API key
export PATH="$HOME/.local/bin:$PATH" && uv run python -m dakora.cli config --provider openai
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

## Playground UI Development

The playground web interface is built with React, TypeScript, Vite, and shadcn/ui. It uses a modular Cockpit architecture for extensibility.

**Build System:**
```bash
# Build the UI (outputs to playground/ directory)
cd web && npm run build

# The playground/ directory structure:
playground/
├── .gitkeep           # IMPORTANT: Keeps directory in git when empty
├── index.html         # Built HTML (gitignored)
└── assets/            # Built JS/CSS bundles (gitignored)
```

**Why .gitkeep Matters:**
- `playground/` build artifacts are gitignored (see `.gitignore`)
- `.gitkeep` ensures the directory exists in git
- CI builds the UI fresh during deployment
- Local development: build manually before running `dakora playground`

**Running the Playground:**
```bash
# From project root (requires dakora.yaml config file)
uv run dakora playground

# Common options:
--port 3000          # Custom port (default: 3000)
--no-browser         # Don't auto-open browser
--demo               # Demo mode (read-only, example templates)
--no-build           # Skip UI build (use existing)
```

**UI Architecture:**

```
web/src/
├── components/
│   ├── layout/              # Layout system
│   │   ├── TopBar.tsx       # Horizontal navigation with tabs
│   │   ├── Sidebar.tsx      # Collapsible sidebar wrapper
│   │   └── MainLayout.tsx   # Layout orchestrator
│   ├── TemplateList.tsx     # Template sidebar content
│   ├── TemplateEditor.tsx   # Template editing/rendering
│   ├── StatusBar.tsx        # Footer status bar
│   └── ui/                  # shadcn/ui components
├── views/
│   └── TemplatesView.tsx    # Templates tab view
├── hooks/
│   └── useApi.ts            # API client hooks
└── App.tsx                  # Main app entry point
```

**Adding New Features:**

1. **New Tab (e.g., Compare, Analytics):**
   - Add tab definition to `TopBar.tsx` tabs array
   - Create new view component in `views/` (e.g., `CompareView.tsx`)
   - Add case to `App.tsx` renderView() switch
   - Return `{ sidebar, content }` from view component

2. **New Sidebar Content:**
   - Views control their own sidebar via returned `sidebar` prop
   - Sidebar automatically swaps when tab changes
   - Example: `CompareView.tsx` returns model selector in sidebar

3. **Shared Components:**
   - Add to `components/` for reusable UI elements
   - Use shadcn/ui components from `components/ui/`
   - Follow existing patterns (StatusBar, TemplateEditor)

**Development Workflow:**
```bash
# 1. Make UI changes in web/src/
# 2. Build the UI
cd web && npm run build

# 3. Test locally
cd .. && uv run dakora playground --no-browser

# 4. Validate with Playwright if needed
# (Playwright MCP is available for automated testing)
```

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
├── web/                     # Playground UI source
│   ├── src/
│   │   ├── components/      # React components
│   │   │   ├── layout/      # Layout system (TopBar, Sidebar, MainLayout)
│   │   │   └── ui/          # shadcn/ui components
│   │   ├── views/           # Tab view components
│   │   ├── hooks/           # React hooks (API client)
│   │   └── App.tsx          # Main application
│   └── package.json
├── playground/              # Built UI (gitignored except .gitkeep)
│   └── .gitkeep            # Keeps directory in git
├── tests/                   # Test suite
├── prompts/                 # Example templates
└── pyproject.toml           # Project metadata