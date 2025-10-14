# Dakora

<p align="center">
  <img src="assets/logo.svg" alt="Dakora Logo" width="200">
</p>

[![CI](https://github.com/bogdan-pistol/dakora/workflows/CI/badge.svg)](https://github.com/bogdan-pistol/dakora/actions)
[![codecov](https://codecov.io/gh/bogdan-pistol/dakora/branch/main/graph/badge.svg)](https://codecov.io/gh/bogdan-pistol/dakora)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![PyPI version](https://badge.fury.io/py/dakora.svg)](https://badge.fury.io/py/dakora)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Discord](https://img.shields.io/discord/1422246380096720969?style=for-the-badge&color=667eea&label=Community&logo=discord&logoColor=white)](https://discord.gg/QSRRcFjzE8)

A Python library for managing and executing LLM prompts with type-safe inputs, versioning, and an interactive web playground. Execute templates against 100+ LLM providers with built-in cost tracking.

## 🚀 Try it Now - No Installation Required

**[playground.dakora.io](https://playground.dakora.io/)** - Experience Dakora's interactive playground directly in your browser. Edit templates, test inputs, and see instant results with the exact same interface that ships with the Python package.

## Use Case

```python
from dakora import Vault, LocalRegistry

vault = Vault(LocalRegistry("./prompts"))

# Execute against any LLM provider
result = vault.get("summarizer").execute(
    model="gpt-4",
    input_text="Your article here..."
)

print(result.output)          # The LLM's response
print(f"${result.cost_usd}")  # Track costs automatically
```

**Multiple ways to initialize:**

```python
# Direct registry injection (recommended)
vault = Vault(LocalRegistry("./prompts"))

# Azure Blob Storage
from dakora import AzureRegistry
vault = Vault(AzureRegistry(
    container="prompts",
    account_url="https://myaccount.blob.core.windows.net"
))

# Config file (for CLI tools)
vault = Vault.from_config("dakora.yaml")

# Legacy shorthand
vault = Vault(prompt_dir="./prompts")
```

Or from the command line:

```bash
dakora run summarizer --model gpt-4 --input-text "Article..."
```

## Features

- 🌐 **[Live Web Playground](https://playground.dakora.io/)** - Try online without installing anything!
- 🎯 **Local Playground** - Same modern React UI included with pip install
- 🚀 **LLM Execution** - Run templates against 100+ LLM providers (OpenAI, Anthropic, Google, etc.)
- 🎨 **Type-safe prompt templates** with validation and coercion
- 📁 **File-based template management** with YAML definitions
- 🔄 **Hot-reload support** for development
- 📝 **Jinja2 templating** with custom filters
- 🏷️ **Semantic versioning** for templates
- 📊 **Optional execution logging** to SQLite with cost tracking
- 🖥️ **CLI interface** for template management and execution
- 🧵 **Thread-safe caching** for production use
- 💰 **Cost & performance tracking** - Monitor tokens, latency, and costs

## Installation

```bash
pip install dakora
```

**For the interactive playground**:

- PyPI releases include a pre-built UI - just run `dakora playground`
- For development installs (git clone), Node.js 18+ is required
- The UI builds automatically from source on first run if not present

Or for development:

```bash
git clone https://github.com/bogdan-pistol/dakora.git
cd dakora
uv sync
source .venv/bin/activate
```

## Quick Start

### 1. Initialize a project

```bash
dakora init
```

This creates:

- `dakora.yaml` - Configuration file
- `prompts/` - Directory for template files
- `prompts/summarizer.yaml` - Example template

### 2. Create a template

Create `prompts/greeting.yaml`:

```yaml
id: greeting
version: 1.0.0
description: A personalized greeting template
template: |
  Hello {{ name }}!
  {% if age %}You are {{ age }} years old.{% endif %}
  {{ message | default("Have a great day!") }}
inputs:
  name:
    type: string
    required: true
  age:
    type: number
    required: false
  message:
    type: string
    required: false
    default: "Welcome to Dakora!"
```

### 3. Use in Python

```python
from dakora import Vault

# Initialize vault
vault = Vault("dakora.yaml")

# Get and render template
template = vault.get("greeting")
result = template.render(name="Alice", age=25)
print(result)
# Output:
# Hello Alice!
# You are 25 years old.
# Welcome to Dakora!
```

### 4. Interactive Playground 🎯

#### Try Online - No Installation Required

Visit **[playground.dakora.io](https://playground.dakora.io/)** to experience the playground instantly in your browser with example templates.

#### Or Run Locally

Launch the same web-based playground locally (included with pip install):

```bash
dakora playground
```

![Playground Demo](assets/playground-demo.gif)

This **automatically**:

- 🔨 Builds the modern React UI (first run only)
- 🚀 Starts the server at `http://localhost:3000`
- 🌐 Opens your browser to the playground

**Features:**

- ✨ **Identical experience** online and locally
- 📱 Mobile-friendly design that works on all screen sizes
- 🎨 Real-time template editing and preview
- 🧪 Test templates with different inputs
- 📊 Example templates for inspiration
- 💻 Modern UI built with shadcn/ui components

![Playground Interface](assets/playground-interface.png)

**Local Options:**

```bash
dakora playground --port 8080      # Custom port
dakora playground --no-browser     # Don't open browser
dakora playground --no-build       # Skip UI build
dakora playground --demo           # Run in demo mode (like the web version)
```

### 5. Execute Templates with LLMs

Dakora can execute templates against real LLM providers (OpenAI, Anthropic, Google, etc.) using the integrated LiteLLM support.

### Setting API Keys

Get an API Key from your LLM provider, you will need an account:

- [Open AI](https://platform.openai.com/docs/libraries#create-and-export-an-api-key)
- [Anthropic](https://docs.claude.com/en/docs/get-started)
- [Google](https://ai.google.dev/gemini-api/docs/api-key#api-keys)

Set your API Key as environment variables:

<details>
<summary>Linux/MacOS</summary>

```zsh
export OPENAI_API_KEY="your_key_here"
export ANTHROPIC_API_KEY="your_key_here"
export GOOGLE_API_KEY="your_key_here"
```

</details>

<details>
<summary>Windows</summary>

```bash
setx OPENAI_API_KEY "your_api_key_here"
setx ANTHROPIC_API_KEY=your_key_here
setx GOOGLE_API_KEY=your_key_here
```

</details>

<details>
<summary>Cross-platform</summary>
Alternatively create a .env file in your project root:

```bash
OPENAI_API_KEY="your_key_here"
GOOGLE_API_KEY="your_key_here"
ANTHROPIC_API_KEY="your-api-key-here"
```

Load and use in your Python code:

```python
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Access variables using os.environ or os.getenv()
api_key = os.getenv("OPENAI_API_KEY")

#initialise the LLM Client
```

## Warning

Nerver commit your API key to version control.
Add .env to your .gitignore with:

```bash
echo ".env" >> .gitignore
```

</details>

### Execute from Python

```python
from dakora import Vault

vault = Vault("dakora.yaml")
template = vault.get("summarizer")

# Execute with gpt-4
result = template.execute(
    model="gpt-4",
    input_text="Your article content here..."
)

print(result.output)
print(f"Cost: ${result.cost_usd:.4f}")
print(f"Tokens: {result.tokens_in} → {result.tokens_out}")
```

#### Execute from CLI

```bash
# Basic execution
dakora run summarizer --model gpt-4 --input-text "Article to summarize..."

# With LLM parameters
dakora run summarizer --model gpt-4 \
  --input-text "Article..." \
  --temperature 0.7 \
  --max-tokens 100

# JSON output for scripting
dakora run summarizer --model gpt-4 \
  --input-text "Article..." \
  --json

# Quiet mode (only LLM response)
dakora run summarizer --model gpt-4 \
  --input-text "Article..." \
  --quiet
```

**Example Output:**

```text
╭─────────────────────────────────────╮
│ Model: gpt-4 (openai)               │
│ Cost: $0.0045 USD                   │
│ Latency: 1,234 ms                   │
│ Tokens: 150 → 80                    │
╰─────────────────────────────────────╯

The article discusses the recent advances in...
```

#### Compare Multiple Models

Compare the same prompt across different models to find the best one for your use case.

**Prerequisites:** You need API keys for each provider you want to compare. See the [Setting API Keys](#setting-api-keys) section above for setup instructions.

**From Python:**

```python
from dakora import Vault

vault = Vault("dakora.yaml")
template = vault.get("summarizer")

# Compare across multiple models in parallel
# Note: You need OPENAI_API_KEY, ANTHROPIC_API_KEY, and GOOGLE_API_KEY set
comparison = template.compare(
    models=["gpt-4", "claude-3-opus", "gemini-pro"],
    input_text="Your article content here...",
    temperature=0.7
)

# View aggregate stats
print(f"Total Cost: ${comparison.total_cost_usd:.4f}")
print(f"Successful: {comparison.successful_count}/{len(comparison.results)}")
print(f"Total Tokens: {comparison.total_tokens_in} → {comparison.total_tokens_out}")

# Compare individual results
for result in comparison.results:
    if result.error:
        print(f"❌ {result.model}: {result.error}")
    else:
        print(f"✅ {result.model} (${result.cost_usd:.4f}, {result.latency_ms}ms)")
        print(f"   {result.output[:100]}...")
```

**Example Output:**

```text
Total Cost: $0.0890
Successful: 3/3
Total Tokens: 450 → 180

✅ gpt-4 ($0.0450, 1234ms)
   The article discusses recent advances in artificial intelligence and their impact on...
✅ claude-3-opus ($0.0320, 987ms)
   Recent AI developments have transformed multiple industries. The article examines...
✅ gemini-pro ($0.0120, 1567ms)
   This piece explores cutting-edge AI technologies and analyzes their effects across...
```

**Key Features:**

- ⚡ **Parallel execution** - All models run simultaneously for speed
- 💪 **Handles failures gracefully** - One model failing doesn't stop others (e.g., missing API key)
- 📊 **Rich comparison data** - Costs, tokens, latency for each model
- 🔄 **Order preserved** - Results match input model order
- 📝 **All executions logged** - Each execution tracked separately

**Why Compare Models?**

- Find the most cost-effective model for your use case
- Test quality differences between providers
- Evaluate latency trade-offs
- Build fallback strategies for production

#### Supported Models

Dakora supports 100+ LLM providers through LiteLLM:

- **OpenAI:** `gpt-4`, `gpt-4-turbo`, `gpt-5-nano`, `gpt-3.5-turbo`
- **Anthropic:** `claude-3-opus`, `claude-3-sonnet`, `claude-3-haiku`
- **Google:** `gemini-pro`, `gemini-1.5-pro`
- **Local:** `ollama/llama3`, `ollama/mistral`
- **And many more...**

See [LiteLLM docs](https://docs.litellm.ai/docs/providers) for the full list.

### 6. CLI Usage

![CLI Workflow](assets/cli-workflow.gif)

```bash
# List all templates
dakora list

# Get template content
dakora get greeting

# Execute a template
dakora run summarizer --model gpt-4 --input-text "..."

# Bump version
dakora bump greeting --minor

# Watch for changes
dakora watch

```


![CLI Output](assets/cli-output.png)

### Verify API Keys

Check which API keys are configured:

``` bash
# Check all providers
dakora config

# Check specific provider
dakora config --provider openai
```

## Template Format

Templates are defined in YAML files with the following structure:

![Template Editing](assets/template-editing.png)

```yaml
id: unique_template_id          # Required: Template identifier
version: 1.0.0                  # Required: Semantic version
description: Template purpose   # Optional: Human-readable description
template: |                     # Required: Jinja2 template string
  Your template content here
  {{ variable_name }}
inputs:                         # Optional: Input specifications
  variable_name:
    type: string                # string|number|boolean|array<string>|object
    required: true              # Default: true
    default: "default value"    # Optional: Default value
metadata:                       # Optional: Custom metadata
  tags: ["tag1", "tag2"]
  author: "Your Name"
```

### Supported Input Types

- `string` - Text values
- `number` - Numeric values (int/float)
- `boolean` - True/false values
- `array<string>` - List of strings
- `object` - Dictionary/JSON object

### Built-in Jinja2 Filters

- `default(value)` - Provide fallback for empty values
- `yaml` - Convert objects to YAML format

## Configuration

### Local Storage (Default)

`dakora.yaml` structure for local file storage:

```yaml
registry: local                 # Registry type
prompt_dir: ./prompts          # Path to templates directory
logging:                       # Optional: Execution logging
  enabled: true
  backend: sqlite
  db_path: ./dakora.db
```

### Azure Blob Storage

For cloud-based template storage with Azure Blob Storage:

**Install Azure dependencies:**

```bash
pip install dakora[azure]
```

**Python usage:**

```python

from dakora import Vault, AzureRegistry

# Option 1: Direct initialization with DefaultAzureCredential
vault = Vault(AzureRegistry(
    container="prompts",
    account_url="https://myaccount.blob.core.windows.net"
    # Uses DefaultAzureCredential (Azure CLI, Managed Identity, etc.)
))

# Option 2: With connection string
vault = Vault(AzureRegistry(
    container="prompts",
    connection_string="DefaultEndpointsProtocol=https;AccountName=..."
))

# Option 3: From config file
vault = Vault.from_config("dakora.yaml")

# Use normally - same API as local storage
template = vault.get("greeting")
result = template.render(name="Alice")
```

**Configuration file (`dakora.yaml`):**

```yaml

registry: azure
azure_container: prompts                    # Azure Blob container name
azure_account_url: https://myaccount.blob.core.windows.net
# Optional: Connection string (alternative to account_url)
# azure_connection_string: "DefaultEndpointsProtocol=https;..."
# Optional: Custom prefix for blob paths
# azure_prefix: prompts/
logging:                                    # Optional: Same as local
  enabled: true
  backend: sqlite
  db_path: ./dakora.db

```

**Authentication:**

AzureRegistry supports multiple authentication methods:

1. **DefaultAzureCredential (Recommended)** - Automatically tries multiple methods:
   - Azure CLI (`az login`)
   - Managed Identity (when running on Azure)
   - Environment variables
   - Visual Studio Code
   - And more...

2. **Connection String** - Direct connection string with account key:

   ```python
   vault = Vault(AzureRegistry(
       container="prompts",
       connection_string=os.environ["AZURE_STORAGE_CONNECTION_STRING"]
   ))
   ```

**Environment Variables:**

```bash
# For DefaultAzureCredential (recommended)
az login  # Authenticate via Azure CLI

# Or use connection string
export AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=myaccount;AccountKey=..."
```

**Features:**

- ✅ Same API as local storage - just swap the registry
- ✅ Thread-safe with caching
- ✅ List, load, and save templates to Azure Blob Storage
- ✅ Works with all Dakora features (CLI, playground, execution)
- ✅ Secure authentication via Azure credentials

**CLI Usage:**

```bash
# All CLI commands work with Azure registry
dakora list                    # Lists templates from Azure
dakora get greeting            # Loads from Azure Blob Storage
dakora run summarizer --model gpt-4 --input-text "..."

# Playground works too
dakora playground              # Uses Azure registry from config
```

## Advanced Usage

### FastAPI + OpenAI Integration

Dakora works great with web APIs. Here's a FastAPI example using OpenAI's latest Responses API and GPT-5:

```python
from fastapi import FastAPI
from dakora import Vault
from openai import OpenAI

app = FastAPI()
vault = Vault("dakora.yaml")
client = OpenAI()

@app.post("/chat")
async def chat_endpoint(message: str, template_id: str):
    template = vault.get(template_id)

    # Use template's run method with new Responses API
    result = template.run(
        lambda prompt: client.responses.create(
            model="gpt-5",
            reasoning={"effort": "medium"},
            input=prompt
        ).output_text,
        message=message
    )

    return {"response": result}
```

## Examples

### Multi-Agent Research Assistant

**[examples/openai-agents/](examples/openai-agents/)** - Build intelligent research agents with the OpenAI Agents Framework, using Dakora to manage complex multi-agent prompts with type-safe inputs and hot-reload during development.

### FastAPI Integration

See [examples/fastapi/](examples/fastapi/) for a complete FastAPI application with multiple endpoints, reasoning controls, and error handling.

### With Logging

```python
from dakora import Vault

vault = Vault("dakora.yaml")
template = vault.get("my_template")

# Log execution automatically
result = template.run(
    lambda prompt: call_your_llm(prompt),
    input_text="Hello world"
)
```

### Direct Vault Creation

```python
from dakora import Vault

# Skip config file, use prompt directory directly
vault = Vault(prompt_dir="./my_prompts")
```

### Hot Reload in Development

```python
from dakora import Vault
from dakora.watcher import Watcher

vault = Vault("dakora.yaml")
watcher = Watcher("./prompts", on_change=vault.invalidate_cache)
watcher.start()

# Templates will reload automatically when files change
```

## Development

### Setup

```bash
git clone https://github.com/bogdan-pistol/dakora.git
cd dakora
uv sync
source .venv/bin/activate
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=dakora

# Run smoke tests
uv run python tests/smoke_test.py
```

### Code Quality

```bash
# Format code
uv run ruff format

# Lint code
uv run ruff check

# Type checking
uv run mypy dakora
```

### Development Commands

See [CLAUDE.md](CLAUDE.md) for detailed development guidance.

## Contributing

We welcome contributions! Join our community:

- 💬 **[Discord](https://discord.gg/QSRRcFjzE8)** - Join our Discord server for discussions and support
- 🐛 **Issues** - Report bugs or request features
- 🔀 **Pull Requests** - Submit improvements

### Development Setup

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and add tests
4. Run the test suite: `uv run pytest`
5. Submit a pull request

## License

This project is licensed under the Apache-2.0 License - see the [LICENSE](LICENSE) file for details.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.
