# GitHub Copilot Instructions for Dakora

## Project Overview

Dakora is an AI Control Plane for Prompt Management - a monorepo platform that enables developers to manage and execute LLM prompts with type-safe inputs, versioning, and multi-model comparison capabilities.

## Architecture

This is a **monorepo** with a **Docker-first architecture** containing:

- **server/**: FastAPI backend server (Python 3.11+)
- **studio/**: React/TypeScript frontend UI (Vite + Tailwind CSS)
- **cli/**: Command-line interface tools (Python)
- **packages/client-python/**: Python client library for interacting with Dakora
- **dakora/**: Core Python package with LLM integrations and registry
- **examples/**: Integration examples (FastAPI, OpenAI, Microsoft Agent Framework)
- **docs/**: MDX documentation

## Technology Stack

### Backend (Python)
- **Framework**: FastAPI with Uvicorn
- **Python Version**: 3.11+
- **Package Manager**: uv (modern Python package manager)
- **Key Dependencies**: 
  - Pydantic v2 for data validation
  - LiteLLM for multi-LLM support
  - Jinja2 for templating
  - Azure SDK (optional for Azure integrations)
- **Testing**: pytest with pytest-asyncio

### Frontend (TypeScript)
- **Framework**: React with TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **Code Editor**: Monaco Editor integration

### Infrastructure
- **Containerization**: Docker & Docker Compose
- **Deployment**: Railway support (railway.toml)

## Coding Standards & Conventions

### Python Code
1. **Type Hints**: Always use type hints for function parameters and return values
2. **Async/Await**: Use async/await patterns for I/O operations
3. **Pydantic Models**: Use Pydantic v2 models for data validation and settings
4. **Docstrings**: Use Google-style docstrings for functions and classes
5. **Imports**: Group imports (standard library, third-party, local)
6. **Error Handling**: Use FastAPI's HTTPException for API errors
7. **Configuration**: Use Pydantic Settings for environment-based config
8. **Formatting**: Format Python code with Black using the repo `pyproject.toml` configuration (line length 88, Python 3.11 targets)
9. **Static Analysis**: Keep Pylance diagnostics clean—resolve missing type hints, `Any` leaks, and other warnings surfaced by Pylance-equivalent type checkers

### TypeScript/React Code
1. **Components**: Use functional components with TypeScript
2. **Hooks**: Prefer custom hooks for reusable logic
3. **Styling**: Use Tailwind CSS utility classes
4. **State Management**: Keep state local when possible
5. **API Calls**: Use proper error handling and loading states
6. **Types**: Define explicit types, avoid `any`

### File Naming
- Python: `snake_case.py`
- TypeScript/React: `PascalCase.tsx` for components, `camelCase.ts` for utilities
- YAML configs: `kebab-case.yaml`

## Project-Specific Patterns

### Prompt Management
- Prompts are stored as YAML files in `prompts/` directory
- Each prompt has metadata including id, name, model, template, and inputs
- Use Jinja2 templating for dynamic prompt generation

### API Structure
- Routes are organized in `server/dakora_server/api/`
- Use FastAPI dependency injection for shared logic
- Return proper HTTP status codes (200, 201, 404, 422, 500)

### LLM Integration
- Support multiple LLM providers via LiteLLM
- Handle streaming and non-streaming responses
- Implement proper error handling for API failures

### Testing
- Write pytest tests in `tests/` and `server/tests/`
- Use `conftest.py` for shared fixtures
- Test both sync and async code paths
- Include smoke tests for critical paths

## Common Tasks

### Adding a New API Endpoint
1. Create route in `server/dakora_server/api/`
2. Define Pydantic request/response models
3. Register router in `main.py`
4. Add tests in `server/tests/`
5. Update OpenAPI docs if needed

### Adding a New Prompt Template
1. Create YAML file in `prompts/`
2. Define inputs, model, and template
3. Test with `dakora execute` CLI command
4. Add to examples if relevant

### Adding a New Frontend Component
1. Create component in `studio/src/components/`
2. Use Radix UI primitives when possible
3. Apply Tailwind styling
4. Export from `components/index.ts` if reusable

### Adding Azure Integration
1. Use `azure-storage-blob` and `azure-identity` packages
2. Implement in `dakora/registry/backends/`
3. Add Azure-specific configuration in settings
4. Mark as optional dependency

## Important Notes

- **Monorepo**: Changes may affect multiple packages - consider dependencies
- **Docker First**: Ensure changes work in containerized environment
- **Backward Compatibility**: Maintain API compatibility when possible
- **Documentation**: Update relevant docs in `docs/` for user-facing changes
- **Examples**: Update examples if API changes affect them
- **Versioning**: Follow semantic versioning for releases
- **Documentation**: Do not generate documentation for changes unless specified

## Security Considerations

- Never commit API keys or secrets
- Use environment variables for sensitive config
- Validate all user inputs with Pydantic
- Sanitize template inputs to prevent injection
- Use CORS appropriately for API endpoints

## Performance Tips

- Use async endpoints for I/O-bound operations
- Implement proper caching where appropriate
- Stream LLM responses for better UX
- Optimize bundle size for frontend

## When in Doubt

- Check existing code patterns in the monorepo
- Refer to FastAPI and Pydantic v2 documentation
- Follow the examples in `examples/` directory
- Maintain consistency with existing code style
