# Dakora Python Client

Python SDK for the Dakora Platform.

## Installation

```bash
pip install dakora-client
```

## Quick Start

```python
from dakora_client import Dakora

# Local (Docker)
dakora = Dakora("http://localhost:54321")

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
dakora = Dakora("https://api.dakora.cloud", api_key="dk_xxx")
result = await dakora.prompts.render("greeting", {"name": "Bob"})
```

## Usage Patterns

### Simple Usage

Define the client once and reuse it throughout your project:

```python
# config.py
from dakora_client import Dakora

dakora = Dakora("http://localhost:54321")
```

```python
# somewhere_else.py
from myapp.config import dakora

async def get_templates():
    return await dakora.prompts.list()
```

### With FastAPI

Use lifespan events for proper cleanup:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from dakora_client import Dakora

dakora = Dakora("http://localhost:54321")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown
    await dakora.close()

app = FastAPI(lifespan=lifespan)

@app.get("/templates")
async def list_templates():
    return await dakora.prompts.list()
```

## API Reference

### `Dakora(url, api_key=None)`

Create a Dakora client instance.

**Parameters:**
- `url` (str): Base URL of the Dakora API server
- `api_key` (str, optional): API key for authentication (required for cloud)

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

## Development

From the monorepo root:

```bash
cd packages/client-python
pip install -e .
```