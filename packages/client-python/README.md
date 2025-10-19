# Dakora Python Client

Python SDK for the Dakora Platform.

## Installation

```bash
pip install dakora-client
```

## Quick Start

```python
from dakora_client import create_client

# Local (Docker)
async with create_client("http://localhost:54321") as dakora:
    # List templates
    templates = await dakora.prompts.list()

    # Get template
    template = await dakora.prompts.get("greeting")

    # Render template
    result = await dakora.prompts.render(
        "greeting",
        inputs={"name": "Alice"}
    )
    print(result.rendered)

# Cloud
async with create_client("https://api.dakora.cloud", api_key="dk_xxx") as dakora:
    result = await dakora.prompts.render("greeting", {"name": "Bob"})
```

## API Reference

### `create_client(url, api_key=None)`

Create a Dakora client instance.

**Parameters:**
- `url` (str): Base URL of the Dakora API server
- `api_key` (str, optional): API key for authentication

**Returns:** `Dakora` client instance

### `Dakora.prompts`

#### `list() -> List[str]`

List all available template IDs.

#### `get(template_id: str) -> TemplateInfo`

Get template details.

#### `render(template_id: str, inputs: dict) -> RenderResult`

Render a template with inputs.

#### `compare(template_id: str, models: List[str], inputs: dict, **params) -> CompareResult`

Compare template execution across multiple LLM models.

### Context Manager

```python
async with create_client(url) as dakora:
    # Client is automatically closed
    pass
```

Or manually:

```python
dakora = create_client(url)
try:
    result = await dakora.prompts.render("template", {"key": "value"})
finally:
    await dakora.close()
```

## Development

From the monorepo root:

```bash
cd packages/client-python
pip install -e .
```