# Dakora Python Client

Python SDK for the Dakora platform.

## Installation

```bash
pip install dakora-client
```

## Quick Start

```python
from dakora_client import create_client

# Local (Docker)
async with create_client("http://localhost:54321") as dakora:
    # Render template
    result = await dakora.prompts.render(
        "greeting",
        inputs={"name": "Alice"}
    )
    print(result.rendered)

# Cloud
async with create_client("https://api.dakora.io", api_key="dk_xxx") as dakora:
    result = await dakora.prompts.render("greeting", {"name": "Bob"})
```

## Documentation

See the [full documentation](https://docs.dakora.io) for:
- Complete API reference
- Advanced usage patterns
- Integration examples
- Best practices

## Development

```bash
cd packages/client-python
pip install -e .
```