# Multi-Agent Research Assistant

Build intelligent research agents using OpenAI Agents Framework with Dakora for clean prompt management.

## What It Does

A multi-agent system that researches any topic by:
1. Breaking it into subtopics
2. Analyzing each area in depth
3. Synthesizing findings into a coherent report

**Tech Stack**: OpenAI Agents Framework + Dakora + Python

## Requirements

- Python 3.11.5+ or 3.12+ (Note: Python 3.11.0-3.11.4 have typing issues with openai-agents)
- OpenAI API key ([get one here](https://platform.openai.com/api-keys))

## Quick Start

### macOS/Linux

```bash
# Clone and navigate to example
cd examples/openai-agents

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up API key
cp .env.example .env
# Edit .env and add: OPENAI_API_KEY=your_key_here

# Run research
python research_assistant.py "AI agent frameworks in 2025"
```

### Windows

```bash
# Clone and navigate to example
cd examples\openai-agents

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up API key
copy .env.example .env
# Edit .env and add: OPENAI_API_KEY=your_key_here

# Run research
python research_assistant.py "AI agent frameworks in 2025"
```

## Agent Architecture

The system uses **3 specialized agents**:

| Agent | Role |
|-------|------|
| **Research Planner** | Breaks topics into subtopics and research questions |
| **Analyst** | Deep dives into each subtopic independently |
| **Synthesizer** | Combines all findings into unified insights |

## Prompt Management with Dakora

All agent instructions live in `prompts/` as version-controlled YAML files:

```
prompts/
├── coordinator_system.yaml    # Orchestration logic
├── planner_system.yaml        # Research strategy
├── analyst_system.yaml        # Analysis framework
├── synthesizer_system.yaml    # Synthesis logic
└── report_template.yaml       # Output formatting
```

### Why Dakora?

**Type-Safe Inputs** - Validate data before it reaches the LLM
```yaml
inputs:
  analysis_depth:
    type: string
    default: standard
  questions:
    type: array<string>
    required: true
```

**Hot Reload** - Edit prompts and re-run without code changes
```bash
# Edit analyst prompt
vim prompts/analyst_system.yaml

# Changes apply immediately
python research_assistant.py "your topic"
```

**Version Control** - Track prompt evolution alongside code
```yaml
id: analyst_system
version: 1.1.0  # Track changes
description: Added economic analysis section
```

**Separation of Concerns** - Agent logic in Python, instructions in YAML

### Dakora Playground

Visualize and test prompts in the interactive UI:

```bash
dakora playground
```

![Dakora Playground](./docs/dakora-playground.png)

## Example Output

```
🔬 Starting research on: AI agent frameworks in 2025

📋 Planning research strategy...

📊 Research Plan:
Strategy: Comprehensive analysis of current landscape
Subtopics: 3

🔍 Analyzing subtopic 1/3: Multi-agent coordination
✓ Analysis complete

🔍 Analyzing subtopic 2/3: Production deployment
✓ Analysis complete

🔍 Analyzing subtopic 3/3: Developer experience
✓ Analysis complete

🔄 Synthesizing findings...
✓ Synthesis complete

================================================================================
📄 RESEARCH REPORT
================================================================================
[Detailed findings and insights...]
================================================================================

💾 Full report saved to: research_output_20250106_143022.json
```

## Customization

### Change Research Depth

Modify parameters in `research_assistant.py`:

```python
result = conduct_research(
    topic="your topic",
    num_subtopics=5,
    focus_areas=["technical", "business"]
)
```

### Update Agent Instructions

Edit any YAML file in `prompts/` - changes apply immediately:

```yaml
# prompts/analyst_system.yaml
template: |
  You are a research analyst...

  Analysis Framework:
  1. Current State
  2. Key Developments
  3. Challenges & Opportunities  # Add more sections here
  4. Expert Perspectives
  5. Future Outlook
```

### Add New Agents

1. Create prompt template in `prompts/new_agent.yaml`
2. Load in Python:
```python
new_agent_prompt = vault.get("new_agent")
new_agent = Agent(
    name="New Agent",
    instructions=new_agent_prompt.render(param="value")
)
```

## How It Works

**OpenAI Agents Framework** handles:
- Multi-agent coordination
- Conversation state management
- Tool execution

**Dakora** handles:
- Prompt template storage
- Input validation and type safety
- Version control
- Hot reloading during development

**Clean separation** = Easier testing, debugging, and iteration

## Project Structure

```
openai-agents/
├── research_assistant.py       # Main script
├── prompts/                    # Dakora templates
│   ├── coordinator_system.yaml
│   ├── planner_system.yaml
│   ├── analyst_system.yaml
│   ├── synthesizer_system.yaml
│   └── report_template.yaml
├── dakora.yaml                 # Dakora config
├── requirements.txt
├── .env.example
└── README.md
```

## Advanced: Handoffs & Guardrails

Add inter-agent handoffs:

```python
from agents import Agent, Handoff

fact_checker = Agent(
    name="Fact Checker",
    instructions=vault.get("fact_checker").render()
)

analyst = Agent(
    name="Analyst",
    instructions=analyst_instructions,
    handoffs=[Handoff(target=fact_checker)]
)
```

Add validation guardrails:

```python
from agents import Guardrail

quality_check = Guardrail(
    instructions=vault.get("quality_guardrail").render(
        criteria={"min_length": 500}
    )
)
```

## Troubleshooting

**"No module named 'agents'"**
```bash
pip install openai-agents
```

**"OPENAI_API_KEY not found"**
```bash
# Make sure .env exists with:
OPENAI_API_KEY=your_actual_key
```

**Prompts not loading**
```bash
# Verify setup
dakora list  # Should show 5+ templates
```

## License

MIT