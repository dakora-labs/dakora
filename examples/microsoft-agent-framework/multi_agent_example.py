#!/usr/bin/env python3
"""
Multi-Agent Orchestrator Example: Microsoft Agent Framework + Dakora

This example demonstrates a sophisticated multi-agent architecture:
- A Router Agent that analyzes user requests and routes to specialized agents
- Multiple specialized agents (Coder, Researcher, Writer, Summarizer)
- Dynamic agent selection based on task requirements
- Dakora templates for each agent's unique instructions
- Agent-to-agent delegation and collaboration

Architecture:
┌─────────────┐
│   User      │
└──────┬──────┘
       │
       v
┌─────────────────┐
│  Router Agent   │  (Analyzes request, selects appropriate agent)
└──────┬──────────┘
       │
       ├─────────────┬─────────────┬─────────────┐
       v             v             v             v
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│  Coder   │  │Researcher│  │  Writer  │  │Summarizer│
└──────────┘  └──────────┘  └──────────┘  └──────────┘

Setup:
1. Run setup script: ./setup.ps1 (Windows) or ./setup.sh (Linux/Mac)
2. Edit .env file with your Azure OpenAI endpoint
3. Login to Azure: az login
4. Run: python multi_agent_planner.py

Features:
- Intelligent task routing based on request analysis
- Specialized agents with domain expertise
- Template-driven agent instructions using Dakora
- Contextual handoffs between agents
"""

import asyncio
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

from agent_framework.azure import AzureOpenAIChatClient
from azure.identity import AzureCliCredential
from dakora import Vault

# Constants
SCRIPT_DIR = Path(__file__).parent
SEPARATOR_WIDTH = 80

# Load environment variables from .env file if it exists
try:
    from load_env import load_env, check_required_vars

    load_env()
    check_required_vars(["AZURE_OPENAI_ENDPOINT"])
except ImportError:
    pass


class TemplateNames(Enum):
    """Centralized template name constants"""

    # Agent definitions (system prompts/personalities)
    AGENT_ROUTER = "agent_router"
    AGENT_CODER = "agent_coder"
    AGENT_RESEARCHER = "agent_researcher"
    AGENT_WRITER = "agent_writer"
    AGENT_SUMMARIZER = "agent_summarizer"
    
    # Task prompts (specific prompts for tasks)
    PROMPT_ROUTING = "prompt_routing"
    PROMPT_WRITE_FROM_RESEARCH = "prompt_write_from_research"
    PROMPT_SUMMARIZE_ARTICLE = "prompt_summarize_article"


class AgentType(Enum):
    """Available specialized agent types"""

    CODER = "coder"
    RESEARCHER = "researcher"
    WRITER = "writer"
    SUMMARIZER = "summarizer"


# Agent configuration - now can use enums directly!
AGENT_CONFIG = {
    AgentType.CODER: {
        "template": TemplateNames.AGENT_CODER,
        "name": "CoderAgent",
    },
    AgentType.RESEARCHER: {
        "template": TemplateNames.AGENT_RESEARCHER,
        "name": "ResearcherAgent",
    },
    AgentType.WRITER: {
        "template": TemplateNames.AGENT_WRITER,
        "name": "WriterAgent",
    },
    AgentType.SUMMARIZER: {
        "template": TemplateNames.AGENT_SUMMARIZER,
        "name": "SummarizerAgent",
    },
}


@dataclass
class AgentResponse:
    """Response from an agent"""

    agent_type: AgentType
    text: str
    thinking: Optional[str] = None


class MultiAgentOrchestrator:
    """
    Orchestrates multiple specialized agents using a router for intelligent routing.
    """

    def __init__(self, vault: Vault, chat_client: AzureOpenAIChatClient):
        self.vault = vault
        self.chat_client = chat_client
        self.agents = {}
        self.router = None

    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize_agents()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.cleanup()
        return False

    async def initialize_agents(self):
        """Initialize all specialized agents with their Dakora templates"""
        try:
            # Create specialized agents using configuration
            for agent_type, config in AGENT_CONFIG.items():
                template_name = config["template"].value
                agent_name = config["name"]

                template = self.vault.get(template_name)
                instructions = template.render()
                self.agents[agent_type] = await self.chat_client.create_agent(
                    instructions=instructions, name=agent_name
                ).__aenter__()

            # Create Router Agent
            # Only list successfully initialized agents
            router_template = self.vault.get(TemplateNames.AGENT_ROUTER.value)
            router_instructions = router_template.render(
                available_agents=[agent.value for agent in self.agents.keys()]
            )
            self.router = await self.chat_client.create_agent(
                instructions=router_instructions, name="RouterAgent"
            ).__aenter__()

            print("✅ All agents initialized successfully")

        except Exception as e:
            print(f"❌ Error initializing agents: {e}")
            await self.cleanup()
            raise

    async def cleanup(self):
        """Clean up all agent resources"""
        for agent in self.agents.values():
            try:
                await agent.__aexit__(None, None, None)
            except Exception as e:
                print(f"⚠️  Error cleaning up agent: {e}")

        if self.router:
            try:
                await self.router.__aexit__(None, None, None)
            except Exception as e:
                print(f"⚠️  Error cleaning up router: {e}")

    async def plan_and_execute(self, user_request: str) -> AgentResponse:
        """
        Use router to analyze request and route to appropriate agent.

        Args:
            user_request: The user's request

        Returns:
            AgentResponse with the result from the selected agent
        """
        print(f"\n{'=' * SEPARATOR_WIDTH}")
        print(f"📥 USER REQUEST: {user_request}")
        print(f"{'=' * SEPARATOR_WIDTH}\n")

        try:
            # Step 1: Ask router to analyze and select agent
            routing_template = self.vault.get(TemplateNames.PROMPT_ROUTING.value)
            routing_prompt = routing_template.render(user_request=user_request)

            print("🤔 Router is analyzing the request...")
            if not self.router:
                raise RuntimeError("Router not initialized. Call initialize_agents() first.")

            router_result = await self.router.run(routing_prompt)
            selected_agent_name = router_result.text.strip().lower()

            # Parse agent selection with exact matching
            selected_agent_type = None
            try:
                # Try exact match first
                selected_agent_type = AgentType(selected_agent_name)
            except ValueError:
                # Fall back to partial matching
                for agent_type in AgentType:
                    if agent_type.value == selected_agent_name:
                        selected_agent_type = agent_type
                        break

            if not selected_agent_type:
                print(
                    f"⚠️  Router response unclear: '{selected_agent_name}', defaulting to RESEARCHER"
                )
                selected_agent_type = AgentType.RESEARCHER

            print(f"🎯 Router selected: {selected_agent_type.value.upper()} agent")
            print(f"{'=' * SEPARATOR_WIDTH}\n")

            # Step 2: Execute request with selected agent
            selected_agent = self.agents[selected_agent_type]
            print(f"🤖 {selected_agent_type.value.upper()} agent is working...\n")

            result = await selected_agent.run(user_request)

            return AgentResponse(
                agent_type=selected_agent_type, text=result.text, thinking=selected_agent_name
            )

        except Exception as e:
            print(f"❌ Error during plan and execute: {e}")
            raise

    async def multi_agent_workflow(self, user_request: str) -> str:
        """
        Execute a complex workflow involving multiple agents in sequence.

        Example: Research -> Write -> Summarize

        Args:
            user_request: The user's request

        Returns:
            Final result after multi-agent collaboration
        """
        print(f"\n{'=' * SEPARATOR_WIDTH}")
        print(f"📥 MULTI-AGENT WORKFLOW: {user_request}")
        print(f"{'=' * SEPARATOR_WIDTH}\n")

        try:
            # Step 1: Research
            print("🔍 STEP 1: Research phase")
            researcher = self.agents[AgentType.RESEARCHER]
            research_result = await researcher.run(user_request)
            print(f"Research output:\n{research_result.text[:200]}...\n")

            # Step 2: Write based on research
            print("✍️  STEP 2: Writing phase")
            writer = self.agents[AgentType.WRITER]
            writing_template = self.vault.get(TemplateNames.PROMPT_WRITE_FROM_RESEARCH.value)
            writing_prompt = writing_template.render(
                research_text=research_result.text, original_request=user_request
            )
            writing_result = await writer.run(writing_prompt)
            print(f"Writing output:\n{writing_result.text[:200]}...\n")

            # Step 3: Summarize
            print("📝 STEP 3: Summarization phase")
            summarizer = self.agents[AgentType.SUMMARIZER]
            summary_template = self.vault.get(TemplateNames.PROMPT_SUMMARIZE_ARTICLE.value)
            summary_prompt = summary_template.render(article_text=writing_result.text)
            summary_result = await summarizer.run(summary_prompt)

            print(f"\n{'=' * SEPARATOR_WIDTH}")
            print("✅ WORKFLOW COMPLETE")
            print(f"{'=' * SEPARATOR_WIDTH}\n")

            return f"""
WORKFLOW RESULTS:
================

RESEARCH FINDINGS:
{research_result.text}

---

ARTICLE:
{writing_result.text}

---

KEY POINTS:
{summary_result.text}
"""

        except Exception as e:
            print(f"❌ Error during multi-agent workflow: {e}")
            raise


def setup_sample_templates():
    """
    Create sample templates for the multi-agent system if they don't exist.
    This ensures the script can run even if templates haven't been set up manually.
    """
    prompts_dir = SCRIPT_DIR / "prompts"
    prompts_dir.mkdir(exist_ok=True)
    
    templates = {
        "agent_router.yaml": """id: agent_router
version: 1.0.0
description: Router agent that analyzes requests and routes to specialized agents
template: |
  You are a Router Agent responsible for analyzing user requests and determining which specialized agent should handle them.
  
  Available agents:
  {% for agent in available_agents %}
  - {{ agent.upper() }}
  {% endfor %}
  
  Agent capabilities:
  - CODER: Handles programming tasks, code writing, debugging, and technical implementation questions
  - RESEARCHER: Handles research queries, factual questions, explanations of concepts, and information gathering
  - WRITER: Handles content creation, blog posts, articles, creative writing, and documentation
  - SUMMARIZER: Handles summarization tasks, creating concise summaries and bullet points
  
  Your job is to:
  1. Analyze the user's request carefully
  2. Determine the PRIMARY intent (what is the main task?)
  3. Select the MOST appropriate agent to handle it
  4. Respond with ONLY the agent type name (lowercase: {% for agent in available_agents %}{{ agent }}{{ ", " if not loop.last else "" }}{% endfor %})
  
  Guidelines:
  - If the request involves writing code or debugging → CODER
  - If the request asks "what is", "explain", "research", or seeks factual information → RESEARCHER
  - If the request asks to write an article, blog post, or creative content → WRITER
  - If the request asks to summarize or create bullet points → SUMMARIZER
  - When in doubt, prefer RESEARCHER for questions and CODER for tasks
  
  Be decisive and pick the single best agent for the job.

inputs:
  available_agents:
    type: array<string>
    description: List of available agent types to route requests to
    required: true

metadata:
  tags: ["router", "routing", "multi-agent", "orchestration", "microsoft-agent-framework"]
  author: "Dakora Examples"
  use_cases: ["agent routing", "task classification", "multi-agent systems", "request orchestration"]
""",
        "agent_coder.yaml": """id: agent_coder
version: 1.0.0
description: Specialized agent for coding tasks and technical implementation
template: |
  You are a Coder Agent - an expert software engineer specializing in writing clean, efficient, and well-documented code.
  
  Your expertise includes:
  - Writing code in multiple programming languages (Python, JavaScript, TypeScript, Java, C#, Go, Rust, etc.)
  - Debugging and troubleshooting code issues
  - Explaining code concepts and best practices
  - Designing algorithms and data structures
  - API integration and web development
  - Database queries and operations
  
  When writing code:
  - Include clear comments explaining the logic
  - Follow best practices and conventions for the language
  - Consider edge cases and error handling
  - Provide complete, runnable examples when possible
  - Explain your approach and any trade-offs
  
  When debugging:
  - Identify the root cause of issues
  - Suggest fixes with explanations
  - Provide alternative solutions when applicable
  
  Your responses should be:
  - Technical and precise
  - Include working code examples
  - Explain the "why" behind your solutions
  - Professional but approachable
  
  Focus on delivering practical, production-ready code solutions.

inputs: {}

metadata:
  tags: ["coder", "programming", "development", "specialist-agent", "microsoft-agent-framework"]
  author: "Dakora Examples"
  use_cases: ["code generation", "debugging", "technical tasks", "programming assistance", "multi-agent systems"]
""",
        "agent_researcher.yaml": """id: agent_researcher
version: 1.0.0
description: Specialized agent for research and factual information gathering
template: |
  You are a Researcher Agent - an expert at gathering, analyzing, and presenting factual information on a wide range of topics.
  
  Your expertise includes:
  - Scientific and technical topics
  - Current trends and developments in technology, AI, and innovation
  - Historical context and background information
  - Explaining complex concepts in accessible ways
  - Providing comprehensive, well-structured information
  - Citing reasoning and knowledge bases when applicable
  
  When researching:
  - Provide accurate, factual information
  - Explain concepts from multiple angles
  - Include relevant context and background
  - Structure information logically
  - Acknowledge limitations or uncertainties
  
  Your research approach:
  - Start with clear definitions
  - Provide historical context when relevant
  - Explain current state and latest developments
  - Discuss practical applications and implications
  - Anticipate follow-up questions
  
  Your responses should be:
  - Comprehensive yet concise
  - Well-organized with clear sections
  - Factual and objective
  - Accessible to both experts and beginners
  - Include examples to illustrate concepts
  
  Focus on delivering thorough, accurate research that educates and informs.

inputs: {}

metadata:
  tags: ["researcher", "information", "knowledge", "specialist-agent", "microsoft-agent-framework"]
  author: "Dakora Examples"
  use_cases: ["research", "factual queries", "explanations", "information gathering", "multi-agent systems"]
""",
        "agent_writer.yaml": """id: agent_writer
version: 1.0.0
description: Specialized agent for content creation and creative writing
template: |
  You are a Writer Agent - a skilled content creator specializing in crafting engaging, clear, and purposeful written content.
  
  Your expertise includes:
  - Blog posts and articles
  - Technical documentation
  - Marketing copy and content
  - Creative writing and storytelling
  - Educational content
  - Professional communications
  
  When writing content:
  - Create engaging openings that hook the reader
  - Use clear, accessible language appropriate for the audience
  - Structure content with logical flow
  - Include relevant examples and anecdotes
  - End with strong conclusions or calls-to-action
  
  Your writing principles:
  - Clarity over complexity
  - Show, don't just tell
  - Use active voice
  - Vary sentence structure for rhythm
  - Edit ruthlessly for impact
  
  Content structure:
  - Start with a compelling introduction
  - Develop ideas with supporting details
  - Use headings and sections for longer pieces
  - Include transitions between ideas
  - Conclude with key takeaways
  
  Your responses should be:
  - Engaging and reader-friendly
  - Well-structured with clear sections
  - Appropriate in tone for the subject
  - Polished and professional
  - Include relevant formatting (headings, lists, emphasis)
  
  Focus on creating content that informs, engages, and resonates with readers.

inputs: {}

metadata:
  tags: ["writer", "content", "creative", "specialist-agent", "microsoft-agent-framework"]
  author: "Dakora Examples"
  use_cases: ["content creation", "articles", "blog posts", "documentation", "creative writing", "multi-agent systems"]
""",
        "agent_summarizer.yaml": """id: agent_summarizer
version: 1.0.0
description: Specialized agent for summarization and distillation of information
template: |
  You are a Summarizer Agent - an expert at distilling complex information into clear, concise summaries.
  
  Your expertise includes:
  - Creating executive summaries
  - Extracting key points from long texts
  - Distilling complex topics into bullet points
  - Identifying the most important information
  - Creating different summary formats (bullets, paragraphs, highlights)
  
  When summarizing:
  - Identify the core message and main points
  - Eliminate redundancy and unnecessary details
  - Preserve the most important information
  - Maintain accuracy and context
  - Use clear, direct language
  
  Your summarization principles:
  - Accuracy first - never misrepresent the source
  - Brevity - say more with less
  - Clarity - make it easy to understand
  - Completeness - include all essential points
  - Structure - organize logically
  
  Summary formats you can provide:
  - Bullet points (most common)
  - Short paragraphs
  - Executive summary style
  - Key takeaways
  - TL;DR (Too Long; Didn't Read)
  
  Your responses should be:
  - Concise and to the point
  - Well-organized and scannable
  - Free of unnecessary elaboration
  - Accurate representations of the source
  - Include the most critical information
  
  Focus on extracting and presenting the essence of information efficiently.

inputs: {}

metadata:
  tags: ["summarizer", "summary", "distillation", "specialist-agent", "microsoft-agent-framework"]
  author: "Dakora Examples"
  use_cases: ["summarization", "key points extraction", "content distillation", "executive summaries", "multi-agent systems"]
""",
        "prompt_routing.yaml": """id: prompt_routing
version: 1.0.0
description: Prompt for router to analyze and route user requests to appropriate agents
template: |
  Analyze this user request and determine which agent should handle it:
  
  USER REQUEST: {{ user_request }}
  
  Respond with ONLY the agent type (one of: coder, researcher, writer, summarizer).
  Think about what the user is primarily asking for, then respond with just the agent name.

inputs:
  user_request:
    type: string
    required: true
    description: The user's request to be analyzed and routed to the appropriate agent

metadata:
  tags: ["router", "routing", "analysis", "multi-agent", "microsoft-agent-framework"]
  author: "Dakora Examples"
  use_cases: ["request routing", "task classification", "agent orchestration"]
""",
        "prompt_write_from_research.yaml": """id: prompt_write_from_research
version: 1.0.0
description: Prompt for writer agent to create article based on research findings
template: |
  Based on this research, write a comprehensive article:
  
  RESEARCH:
  {{ research_text }}
  
  ORIGINAL REQUEST: {{ original_request }}

inputs:
  research_text:
    type: string
    required: true
    description: The research findings to base the article on
  original_request:
    type: string
    required: true
    description: The original user request for context and article direction

metadata:
  tags: ["writing", "workflow", "multi-agent", "research-to-article", "microsoft-agent-framework"]
  author: "Dakora Examples"
  use_cases: ["article writing", "content creation from research", "multi-agent workflows"]
""",
        "prompt_summarize_article.yaml": """id: prompt_summarize_article
version: 1.0.0
description: Prompt for summarizer agent to create key points from an article
template: |
  Summarize this article into key points:
  
  {{ article_text }}

inputs:
  article_text:
    type: string
    required: true
    description: The article text to summarize into key points

metadata:
  tags: ["summarization", "workflow", "multi-agent", "key-points", "microsoft-agent-framework"]
  author: "Dakora Examples"
  use_cases: ["article summarization", "key point extraction", "multi-agent workflows"]
""",
    }
    
    created_count = 0
    for filename, content in templates.items():
        template_path = prompts_dir / filename
        # Create template if it doesn't exist or if it's empty (from previous failed writes)
        if not template_path.exists() or template_path.stat().st_size == 0:
            template_path.write_text(content, encoding='utf-8')
            created_count += 1
            print(f"✓ Created template: {filename}")
    
    if created_count == 0:
        print("✓ All templates already exist")
    else:
        print(f"\n✓ Created {created_count} template(s)")


async def _setup_orchestrator() -> MultiAgentOrchestrator:
    """
    Create and initialize the orchestrator with proper authentication.

    Returns:
        Initialized MultiAgentOrchestrator instance
    """
    vault = Vault(prompt_dir=str(SCRIPT_DIR / "prompts"))
    api_key = os.environ.get("AZURE_OPENAI_API_KEY")

    if api_key:
        print("🔑 Using API Key authentication\n")
        chat_client = AzureOpenAIChatClient()
    else:
        print("🔐 Using Azure CLI authentication\n")
        credential = AzureCliCredential()
        chat_client = AzureOpenAIChatClient(credential=credential)

    orchestrator = MultiAgentOrchestrator(vault, chat_client)
    await orchestrator.initialize_agents()
    return orchestrator


async def demo_single_routing():
    """Demonstrate single request routing to appropriate agent"""
    print(f"\n{'=' * SEPARATOR_WIDTH}")
    print("DEMO 1: INTELLIGENT SINGLE-AGENT ROUTING")
    print(f"{'=' * SEPARATOR_WIDTH}")

    orchestrator = await _setup_orchestrator()

    # Test different types of requests
    test_requests = [
        "Write a Python function to calculate Fibonacci numbers",
        "What are the latest trends in artificial intelligence?",
        "Write a blog post about the benefits of meditation",
        "Summarize the key concepts of machine learning in 3 bullet points",
    ]

    try:
        for request in test_requests:
            response = await orchestrator.plan_and_execute(request)

            print(f"🤖 AGENT: {response.agent_type.value.upper()}")
            print(f"📤 RESPONSE:\n{response.text}\n")
            print(f"{'=' * SEPARATOR_WIDTH}\n")

            # Add a small delay between requests
            await asyncio.sleep(1)

    finally:
        await orchestrator.cleanup()


async def demo_multi_agent_workflow():
    """Demonstrate multi-agent collaboration workflow"""
    print(f"\n{'=' * SEPARATOR_WIDTH}")
    print("DEMO 2: MULTI-AGENT COLLABORATION WORKFLOW")
    print(f"{'=' * SEPARATOR_WIDTH}")

    orchestrator = await _setup_orchestrator()

    try:
        # Complex task requiring multiple agents
        task = "Explain the concept of quantum computing and its potential applications"

        result = await orchestrator.multi_agent_workflow(task)
        print(result)

    finally:
        await orchestrator.cleanup()


async def interactive_mode():
    """Interactive mode for testing the multi-agent system"""
    print(f"\n{'=' * SEPARATOR_WIDTH}")
    print("INTERACTIVE MULTI-AGENT SYSTEM")
    print(f"{'=' * SEPARATOR_WIDTH}")

    orchestrator = await _setup_orchestrator()

    print("\n💡 Type your requests, or 'quit' to exit")
    print("💡 Prefix with 'workflow:' for multi-agent collaboration\n")

    try:
        while True:
            user_input = input("\n👤 You: ").strip()

            if user_input.lower() in ["quit", "exit", "q"]:
                print("\n👋 Goodbye!")
                break

            if not user_input:
                continue

            try:
                if user_input.lower().startswith("workflow:"):
                    # Multi-agent workflow
                    task = user_input[9:].strip()
                    result = await orchestrator.multi_agent_workflow(task)
                    print(result)
                else:
                    # Single agent routing
                    response = await orchestrator.plan_and_execute(user_input)
                    print(f"\n🤖 {response.agent_type.value.upper()} Agent:")
                    print(f"{response.text}")
            except Exception as e:
                print(f"\n❌ Error processing request: {e}")

    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    finally:
        await orchestrator.cleanup()


async def main():
    """Main entry point"""
    # Check required environment variable
    if not os.environ.get("AZURE_OPENAI_ENDPOINT"):
        print("❌ Error: AZURE_OPENAI_ENDPOINT environment variable not set")
        print("\nPlease either:")
        print("1. Edit .env file and set AZURE_OPENAI_ENDPOINT")
        print(
            "2. Or run: export AZURE_OPENAI_ENDPOINT='https://your-resource.openai.azure.com'"
        )
        return

    # Create sample templates if they don't exist
    setup_sample_templates()

    print("\n🚀 Multi-Agent Orchestrator System with Dakora + Microsoft Agent Framework")
    print("\nChoose a demo mode:")
    print("1. Single-agent routing demo (automated)")
    print("2. Multi-agent workflow demo (automated)")
    print("3. Interactive mode")
    print("4. Run all demos")

    choice = input("\nEnter choice (1-4): ").strip()

    if choice == "1":
        await demo_single_routing()
    elif choice == "2":
        await demo_multi_agent_workflow()
    elif choice == "3":
        await interactive_mode()
    elif choice == "4":
        await demo_single_routing()
        await demo_multi_agent_workflow()
    else:
        print("Invalid choice. Running demo 1...")
        await demo_single_routing()


if __name__ == "__main__":
    asyncio.run(main())
