# Microsoft Agent Framework + Dakora Integration Examples

This example demonstrates how to integrate **Dakora** (prompt template management) with the **Microsoft Agent Framework** (the new official agent framework from Microsoft, released in 2025).

## Quick Start

```bash
# 1. Run setup (creates venv, installs dependencies, creates .env)
cd examples/microsoft-agent-framework
.\setup.ps1  # Windows
# OR
./setup.sh   # Linux/Mac

# 2. Edit .env with your Azure OpenAI endpoint
# AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com

# 3. Login to Azure
az login

# 4. Run simple example
python simple_agent_example.py

# 5. Try multi-agent example
python multi_agent_example.py
```

## Overview

The Microsoft Agent Framework provides a unified way to build AI agents with support for:

- Multiple backends (Azure OpenAI, OpenAI, Azure AI Foundry, etc.)
- Multi-turn conversations with context
- Tool calling and function execution
- Streaming responses
- Multi-agent workflows

By combining it with Dakora, you get:

- **Type-safe prompt templates** with validation
- **Versioned prompts** for A/B testing and rollback
- **Centralized prompt management** across your agent system
- **Dynamic prompt switching** based on context
- **Reusable prompt components** across multiple agents

## Files in This Example

- **`simple_agent_example.py`** - Basic getting-started example showing core Dakora + Agent Framework integration
- **`multi_agent_example.py`** - Advanced multi-agent orchestrator with intelligent routing and specialized agents
- **`load_env.py`** - Utility for loading environment variables from `.env` file
- **`setup.ps1`** / **`setup.sh`** - Automated setup scripts for Windows/Linux/Mac
- **`requirements.txt`** - Python dependencies
- **`prompts/`** - Directory containing all Dakora templates (auto-created by scripts)
- **`.env.example`** - Example environment configuration file

## Installation

### Prerequisites

1. **Python 3.10 or later**

   ```bash
   python --version
   ```

2. **Azure OpenAI or Azure AI Foundry** configured:
   - [Create an Azure OpenAI resource](https://learn.microsoft.com/azure/ai-foundry/openai/how-to/create-resource)
   - Or set up an [Azure AI Foundry project](https://learn.microsoft.com/azure/ai-foundry/)

3. **Azure CLI** installed and authenticated:

   ```bash
   az login
   ```

### Recommended: Automated Setup with Virtual Environment

**Windows (PowerShell):**

```powershell
cd examples/microsoft-agent-framework
.\setup.ps1
```

**Linux/Mac (Bash):**

```bash
cd examples/microsoft-agent-framework
chmod +x setup.sh
./setup.sh
```

The setup script will:

- ✅ Check Python version
- ✅ Create a virtual environment (`venv/`)
- ✅ Install all dependencies in isolation
- ✅ Verify Azure CLI
- ✅ Initialize Dakora

**Why virtual environment?**

- Keeps dependencies isolated from system Python
- Prevents version conflicts
- Easy to delete and recreate
- Best practice for Python projects

### Alternative: Manual Setup

If you prefer manual installation:

```bash
# Create virtual environment
python -m venv venv

# Activate it
# Windows:
.\venv\Scripts\Activate.ps1
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# When done:
deactivate
```

## Configuration

### Quick Start: Using .env File (Recommended)

The easiest way to configure your environment:

1. **Run the setup script** (creates `.env` automatically):

   ```bash
   # Windows: .\setup.ps1
   # Linux/Mac: ./setup.sh
   ```

2. **Edit the `.env` file** with your Azure credentials:

   ```env
   AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
   ```

3. **Login to Azure CLI**:

   ```bash
   az login
   ```

4. **Run examples** - they'll automatically load `.env`:

   ```bash
   python simple_agent_example.py
   ```

### Detailed Configuration Guide

The examples support multiple authentication methods and configuration options:

**Environment Variables:**

```env
# Required
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com

# Optional (if not using Azure CLI)
AZURE_OPENAI_API_KEY=your-api-key

# Alternative: Azure AI Foundry
AZURE_AI_PROJECT_ENDPOINT=https://your-project.services.ai.azure.com
AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4
```

**Authentication Methods:**

1. **Azure CLI (Recommended):**

   ```bash
   az login
   ```

   The examples automatically use `AzureCliCredential()` if no API key is set.

2. **API Key:**
   Set `AZURE_OPENAI_API_KEY` in your `.env` file.

**Platform-Specific Notes:**

- **Windows**: Use `.\setup.ps1` for automated setup
- **Linux/Mac**: Use `./setup.sh` for automated setup
- Both scripts create a virtual environment and configure `.env` file

For troubleshooting and advanced configuration, see the Azure OpenAI and Azure AI Foundry documentation.

### Quick Reference

**Azure OpenAI:**

```env
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
# AZURE_OPENAI_API_KEY=your-key  # Optional if using Azure CLI
```

**Azure AI Foundry:**

```env
AZURE_AI_PROJECT_ENDPOINT=https://your-project.services.ai.azure.com
AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4
```

**Authentication (Recommended):**

```bash
az login
```

## Setup Dakora

**Note:** Both example scripts automatically create required templates on first run, so manual template creation is optional.

If you want to initialize Dakora manually:

```bash
cd examples/microsoft-agent-framework
dakora init
```

The templates are automatically created in the `prompts/` directory when you run either example script.

## Running the Examples

### Example 1: Simple Agent (`simple_agent_example.py`)

The basic getting-started example showing core integration:

```bash
cd examples/microsoft-agent-framework
python simple_agent_example.py
```

**What it demonstrates:**

- Loading and rendering Dakora templates
- Creating an agent with template-based instructions
- Running a simple query
- Auto-creation of templates if they don't exist

**Key concepts:**

- Dakora Vault initialization
- Template rendering with dynamic inputs
- Agent creation with Azure OpenAI
- Authentication (Azure CLI or API Key)

### Example 2: Multi-Agent System (`multi_agent_example.py`)

Advanced example with multiple specialized agents and intelligent routing:

```bash
cd examples/microsoft-agent-framework
python multi_agent_example.py
```

**Interactive menu options:**

1. **Single-agent routing demo** - Automated demo showing router selecting appropriate agents
2. **Multi-agent workflow demo** - Research → Write → Summarize pipeline
3. **Interactive mode** - Chat with the system in real-time
4. **Run all demos** - Execute all demonstrations

**What it demonstrates:**

- Router agent for intelligent task routing
- Multiple specialized agents (Coder, Researcher, Writer, Summarizer)
- Multi-agent collaboration workflows
- Dynamic agent selection based on request analysis
- Template-driven agent personalities and behaviors

**Key concepts:**

- Multi-agent orchestration
- Specialized agent roles
- Agent-to-agent workflows
- Dynamic template selection
- Enum-based configuration

## Template Files

Both example scripts automatically create all required templates on first run. The templates are stored in the `prompts/` directory.

### Templates Used in `simple_agent_example.py`

**`prompts/simple_chat_assistant.yaml`**

A flexible chat assistant template with customizable role and expertise:

```yaml
id: simple_chat_assistant
version: 1.0.0
description: A simple, customizable chat assistant with role and expertise configuration
template: |
  You are a {{ role }}{% if expertise %} with expertise in {{ expertise }}{% endif %}.
  
  Your communication style should be helpful, clear, and professional.
  
  When assisting users:
  - Provide accurate, actionable information
  - Use clear explanations with examples when appropriate
  - Stay focused on the user's needs
  - If you're uncertain about something, acknowledge it

inputs:
  role:
    type: string
    required: true
    description: The role or profession the assistant should embody
  expertise:
    type: string
    required: false
    description: Optional specific area of expertise for this assistant
```

### Templates Used in `multi_agent_example.py`

The multi-agent system uses 8 templates total:

**Agent Templates** (define agent personalities and capabilities):

- `agent_router.yaml` - Router agent that analyzes requests and selects appropriate specialists
- `agent_coder.yaml` - Specialized coding agent for programming tasks
- `agent_researcher.yaml` - Research agent for information gathering
- `agent_writer.yaml` - Content creation agent for articles and documentation
- `agent_summarizer.yaml` - Summarization agent for distilling information

**Task Prompts** (specific prompts for multi-agent workflows):

- `prompt_routing.yaml` - Prompt for router to analyze user requests
- `prompt_write_from_research.yaml` - Prompt for creating articles from research
- `prompt_summarize_article.yaml` - Prompt for summarizing articles into key points

All templates are automatically created when you run `multi_agent_example.py` for the first time.

## Architecture Patterns

### Simple Agent Pattern (`simple_agent_example.py`)

The simple example demonstrates a straightforward integration pattern:

```python
# 1. Initialize Dakora Vault
vault = Vault(prompt_dir="prompts")

# 2. Load and render template
template = vault.get("simple_chat_assistant")
instructions = template.render(
    role="Helpful coding assistant",
    expertise="Python programming and best practices"
)

# 3. Create agent with rendered instructions
chat_client = AzureOpenAIChatClient(credential=AzureCliCredential())
async with chat_client.create_agent(
    instructions=instructions,
    name="PythonAssistant"
) as agent:
    # 4. Run queries
    result = await agent.run("How do I read a CSV file in Python?")
    print(result.text)
```

**Benefits:**

- Clean separation of prompts from code
- Type-safe template validation
- Easy to test different prompt versions
- Reusable templates across agents

### Multi-Agent Orchestrator Pattern (`multi_agent_example.py`)

The multi-agent example demonstrates a sophisticated orchestration pattern:

```python
class MultiAgentOrchestrator:
    """Orchestrates multiple specialized agents using a router."""
    
    def __init__(self, vault: Vault, chat_client: AzureOpenAIChatClient):
        self.vault = vault
        self.chat_client = chat_client
        self.agents = {}  # Specialized agents
        self.router = None  # Router agent
    
    async def initialize_agents(self):
        """Create all agents from Dakora templates"""
        # Create specialized agents (coder, researcher, writer, summarizer)
        for agent_type, config in AGENT_CONFIG.items():
            template = self.vault.get(config["template"].value)
            instructions = template.render()
            self.agents[agent_type] = await self.chat_client.create_agent(
                instructions=instructions,
                name=config["name"]
            ).__aenter__()
        
        # Create router agent
        router_template = self.vault.get("agent_router")
        router_instructions = router_template.render(
            available_agents=list(self.agents.keys())
        )
        self.router = await self.chat_client.create_agent(
            instructions=router_instructions,
            name="RouterAgent"
        ).__aenter__()
    
    async def plan_and_execute(self, user_request: str):
        """Route request to appropriate agent"""
        # 1. Router analyzes request
        routing_template = self.vault.get("prompt_routing")
        routing_prompt = routing_template.render(user_request=user_request)
        router_result = await self.router.run(routing_prompt)
        
        # 2. Execute with selected agent
        selected_agent = self.agents[router_result.text]
        return await selected_agent.run(user_request)
```

**Benefits:**

- Intelligent task routing based on request analysis
- Specialized agents for different domains
- Template-driven agent personalities
- Easy to add new agent types
- Supports complex multi-agent workflows

## Use Cases

### 1. Getting Started (simple_agent_example.py)

Perfect for:

- Learning the basic integration
- Creating single-purpose agents
- Quick prototyping
- Understanding template rendering

### 2. Multi-Agent Systems (multi_agent_example.py)

Use different Dakora templates for specialized agents:

- **Intelligent routing**: Router agent selects the right specialist
- **Domain experts**: Coder, Researcher, Writer, Summarizer agents
- **Workflow orchestration**: Chain multiple agents together
- **Complex tasks**: Research → Write → Summarize pipelines

### 3. Production Applications

Both patterns support:

- **Centralized prompt management**: All prompts in one place
- **Version control**: Track prompt changes with git
- **A/B testing**: Test different prompt formulations
- **Easy rollback**: Revert to previous prompt versions
- **Audit trail**: History of prompt modifications
- **Template reuse**: Share templates across multiple agents

## Microsoft Agent Framework Resources

- **Official Documentation**: <https://learn.microsoft.com/agent-framework/>
- **Quick Start Guide**: <https://learn.microsoft.com/agent-framework/tutorials/quick-start>
- **GitHub Repository**: <https://github.com/microsoft/agent-framework>
- **Python Samples**: <https://github.com/microsoft/agent-framework/tree/main/python/samples>

## Dakora Resources

- **GitHub Repository**: <https://github.com/bogdan-pistol/dakora>
- **Documentation**: <https://github.com/bogdan-pistol/dakora/blob/main/README.md>
- **Live Playground**: <https://playground.dakora.io/>

## Troubleshooting

### Authentication Issues

If you get authentication errors:

```bash
# Re-login with Azure CLI
az login

# Verify your account
az account show

# List available subscriptions
az account list
```

### Missing Templates

Templates are automatically created by the scripts. If you encounter "Template not found" errors:

```bash
# The scripts create templates automatically on first run
python simple_agent_example.py
# or
python multi_agent_example.py

# To verify templates exist:
ls prompts/
```

### Module Not Found

If you get import errors:

```bash
# Reinstall dependencies
pip install -U agent-framework agent-framework-azure azure-identity dakora
```

## Next Steps

1. **Start simple**: Run `simple_agent_example.py` to understand the basics
2. **Explore multi-agent**: Run `multi_agent_example.py` to see advanced patterns
3. **Customize templates**: Edit templates in `prompts/` to fit your needs
4. **Build your own**: Use the patterns to create your own agent applications
5. **Experiment**: Try different agent combinations and workflows
6. **Share your experience**: Join the Dakora Discord or contribute examples

## Contributing

Have ideas for improving this example? Contributions are welcome!

- Report issues: <https://github.com/bogdan-pistol/dakora/issues>
- Submit PRs: <https://github.com/bogdan-pistol/dakora/pulls>
- Join Discord: <https://discord.gg/QSRRcFjzE8>

## License

This example is licensed under Apache-2.0, same as the Dakora project.
