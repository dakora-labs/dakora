# Tests for dakora-agents

This directory contains comprehensive tests for the `dakora-agents` package.

## Test Structure

- **`conftest.py`**: Pytest fixtures and test configuration
- **`test_middleware.py`**: Tests for `DakoraTraceMiddleware` class
- **`test_helpers.py`**: Tests for helper functions (`to_message`, etc.)
- **`test_integration.py`**: Integration tests simulating real-world usage

## Running Tests

### Run all tests

```bash
cd packages/agents
uv run pytest
```

### Run with coverage

```bash
uv run pytest --cov=dakora_agents --cov-report=html
```

### Run specific test file

```bash
uv run pytest tests/test_middleware.py
```

### Run specific test

```bash
uv run pytest tests/test_middleware.py::TestDakoraTraceMiddleware::test_middleware_initialization
```

### Run with verbose output

```bash
uv run pytest -v
```

## Test Coverage

The test suite covers:

### Middleware Tests (`test_middleware.py`)
- ✅ Initialization with required/optional parameters
- ✅ Trace metadata injection into context
- ✅ Trace creation with Dakora API
- ✅ Template metadata extraction and tracking
- ✅ Latency calculation
- ✅ Agent ID inclusion
- ✅ Error handling (graceful degradation)
- ✅ Conversation history preservation
- ✅ Helper function (`create_dakora_middleware`)

### Helper Tests (`test_helpers.py`)
- ✅ `to_message()` basic conversion
- ✅ Custom role assignment
- ✅ Metadata preservation
- ✅ Edge cases (empty metadata, different roles)

### Integration Tests (`test_integration.py`)
- ✅ Agent with middleware integration
- ✅ Complete template workflow (render → to_message → agent)
- ✅ Multi-turn conversations with session tracking
- ✅ Multi-agent workflows with shared sessions

## Adding New Tests

When adding new features to `dakora-agents`, please:

1. Add unit tests in the appropriate test file
2. Add integration tests if the feature involves multiple components
3. Update fixtures in `conftest.py` if needed
4. Run the full test suite before committing

## Mocking Strategy

Tests use `unittest.mock` to avoid requiring:
- Real Dakora server
- Real OpenAI API keys
- Real LLM calls

This makes tests:
- ✅ Fast (no network calls)
- ✅ Reliable (no external dependencies)
- ✅ Deterministic (consistent results)
