# Dakora Examples

Real-world integration examples showing how to use Dakora in production applications.

## Microsoft Agent Framework

**Location:** [`microsoft-agent-framework/`](microsoft-agent-framework/)

Multi-agent orchestration with Dakora observability.

**What's included:**
- Simple single-agent example
- Advanced multi-agent orchestration with routing
- Session tracking across multiple agents
- Auto-generated prompt templates

**Quick start:**
```bash
cd microsoft-agent-framework
./setup.sh  # or setup.ps1 on Windows
python simple_agent_example.py
```

See [full MAF example documentation](microsoft-agent-framework/README.md)

## FastAPI + OpenAI

**Location:** [`openai-agents/`](openai-agents/)

REST API demonstrating prompt template management with OpenAI.

**What's included:**
- FastAPI endpoints with template rendering
- OpenAI integration
- Multiple template examples
- Health checks and error handling

**Quick start:**
```bash
cd openai-agents
pip install -r requirements.txt
export OPENAI_API_KEY="your_key"
uvicorn fastapi_openai:app --reload
```

## Contributing Examples

Have a Dakora integration example to share? We'd love to include it!

1. Create a new directory in `examples/`
2. Include a README with setup instructions
3. Add sample code and templates
4. Submit a PR

See [CONTRIBUTING.md](../CONTRIBUTING.md) for details.