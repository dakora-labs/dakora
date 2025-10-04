# Dakora Examples

This directory contains practical examples showing how to use Dakora in real applications.

## Examples Overview

| Example | Description | Framework/Library |
|---------|-------------|-------------------|
| [FastAPI + OpenAI](#fastapi--openai-example) | REST API with OpenAI Responses API | FastAPI, OpenAI |
| [Microsoft Agent Framework](#microsoft-agent-framework-integration) | Multi-agent systems with prompt management | Microsoft Agent Framework |

---

## Microsoft Agent Framework Integration

**NEW!** A comprehensive example showing integration with Microsoft's new Agent Framework (2025 release).

### 🎯 What You'll Learn

- Creating AI agents with Dakora-managed prompts
- Building multi-agent orchestration systems with specialized agents
- Intelligent task routing based on user requests
- Agent-to-agent collaboration workflows
- Dynamic prompt template management

### Example Location

**All files are in:** [`microsoft-agent-framework/`](microsoft-agent-framework/)

This folder contains:

- **Two complete examples**:
  - `simple_agent_example.py` - Basic getting-started example
  - `multi_agent_example.py` - Advanced multi-agent orchestration
- **Setup automation**: `setup.ps1` (Windows) and `setup.sh` (Linux/Mac)
- **Comprehensive documentation**: Full README with architecture patterns
- **9 sample templates**: Auto-generated on first run
- **Environment configuration**: `.env.example` template and helper utilities

### 🚀 Quick Start

```bash
cd microsoft-agent-framework

# Windows
.\setup.ps1

# Linux/Mac
chmod +x setup.sh
./setup.sh

# Run simple getting-started example
python simple_agent_example.py

# Or run advanced multi-agent orchestrator
python multi_agent_example.py
```

### 🌟 Highlights

The example includes:

1. **Two example files**:
   - `simple_agent_example.py` - Simple getting-started example
   - `multi_agent_example.py` - Advanced multi-agent orchestration with routing
2. **Complete demo scenarios**:
   - Single-agent routing with specialized agents (Coder, Researcher, Writer, Summarizer)
   - Multi-agent workflow with agent collaboration
   - Interactive mode for testing
3. **Auto-generated templates** - 9 sample templates created automatically
4. **Production-ready patterns** - DakoraAgentManager class for clean architecture
5. **Setup automation** - Scripts for Windows and Linux/Mac with virtual environment support

**Why combine these two?**

- Microsoft Agent Framework = Powerful agent orchestration
- Dakora = Type-safe, versioned prompt management
- Together = Robust, maintainable AI agent systems

### 📖 Documentation

See [`microsoft-agent-framework/README.md`](microsoft-agent-framework/README.md) for complete documentation.

---

## FastAPI + OpenAI Example

A complete FastAPI application demonstrating Dakora integration with OpenAI's latest Responses API and GPT-5.

### Features

- 🚀 **FastAPI endpoints** for template-based chat
- 🤖 **OpenAI Responses API** integration (recommended for new projects)
- 🧠 **GPT-5 with reasoning** capabilities and effort controls
- 📝 **Multiple template examples** (summarizer, analyzer, chat assistant)
- 🔍 **Template discovery** via REST API
- 📊 **Automatic logging** with Dakora's built-in system
- 🏥 **Health checks** and error handling

### Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up OpenAI API key:**
   ```bash
   export OPENAI_API_KEY="your-api-key-here"
   ```

3. **Initialize Dakora:**
   ```bash
   # Copy example templates
   mkdir -p prompts
   cp templates/* prompts/

   # Or use the CLI to create a fresh project
   dakora init
   ```

4. **Run the API:**
   ```bash
   uvicorn fastapi_openai:app --reload
   ```

5. **Explore the API:**
   - Visit: http://localhost:8000/docs
   - Try the interactive Swagger UI

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/templates` | GET | List all available templates |
| `/templates/{id}` | GET | Get template details |
| `/chat` | POST | Generic chat with any template |
| `/summarize` | POST | Summarize text using summarizer template |
| `/analyze` | POST | Analyze content with analyzer template |
| `/health` | GET | Health check |

### Example Usage

**List templates:**
```bash
curl http://localhost:8000/templates
```

**Chat with assistant:**
```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Explain quantum computing in simple terms",
    "template_id": "chat_assistant",
    "model": "gpt-5",
    "reasoning_effort": "medium",
    "instructions": "Explain in a friendly, accessible way"
  }'
```

**Summarize text:**
```bash
curl -X POST "http://localhost:8000/summarize" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Long article text here...",
    "max_bullets": 3
  }'
```

**Analyze content:**
```bash
curl -X POST "http://localhost:8000/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Business proposal text...",
    "analysis_type": "business"
  }'
```

### Template Examples

The example includes these template files:

- **`analyzer.yaml`** - Content analysis with different types (sentiment, technical, business)
- **`chat_assistant.yaml`** - General purpose chat assistant
- **`summarizer.yaml`** - Text summarization (created by `dakora init`)

### Configuration

The example uses `dakora.yaml` for configuration:

```yaml
registry: local
prompt_dir: ./prompts
logging:
  enabled: true
  backend: sqlite
  db_path: ./dakora.db
```

### Production Considerations

For production use, consider:

- **Authentication**: Add API key validation
- **Rate limiting**: Implement request throttling
- **Monitoring**: Add metrics and alerting
- **Error handling**: Improve error responses
- **Caching**: Cache template renders for repeated requests
- **Async**: Use async OpenAI calls for better performance

### Extending the Example

You can easily extend this example by:

1. **Adding new templates** in the `prompts/` directory
2. **Creating specialized endpoints** for specific use cases
3. **Adding middleware** for logging, authentication, etc.
4. **Integrating with other LLM providers** (Anthropic, etc.)
5. **Adding request validation** and better error handling