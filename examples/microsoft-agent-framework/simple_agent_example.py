#!/usr/bin/env python3
"""
Simple getting started example: Microsoft Agent Framework + Dakora

This is the simplest possible example showing the integration.
Perfect for copy-paste to get started quickly.

Setup:
1. Run setup script: ./setup.ps1 (Windows) or ./setup.sh (Linux/Mac)
2. Edit .env file with your Azure OpenAI endpoint
3. Login to Azure: az login
4. Run: python simple_agent_example.py

Or manually:
1. pip install dakora agent-framework azure-identity
2. Set AZURE_OPENAI_ENDPOINT environment variable
3. az login
4. python simple_agent_example.py

Learn more:
- Dakora docs: https://github.com/bogdan-pistol/dakora
- Microsoft Agent Framework: https://github.com/microsoft/agent-framework
"""

import asyncio
import os
import sys
from pathlib import Path

from agent_framework.azure import AzureOpenAIChatClient
from azure.identity import AzureCliCredential
from dakora import Vault

# Get script directory for relative paths
SCRIPT_DIR = Path(__file__).parent
PROMPTS_DIR = SCRIPT_DIR / "prompts"

# Load environment variables from .env file if it exists
try:
    from load_env import load_env, check_required_vars

    load_env()
    check_required_vars(["AZURE_OPENAI_ENDPOINT"])
except ImportError:
    # load_env.py not available, skip
    pass


def setup_sample_templates(template_name: str = "simple_chat_assistant") -> None:
    """
    Ensure the required template exists, creating it if necessary.
    
    Args:
        template_name: Name of the template to check/create
        
    This function creates a default template file if it doesn't exist,
    so the example can run standalone without requiring setup scripts.
    """
    template_path = PROMPTS_DIR / f"{template_name}.yaml"
    
    # Create prompts directory if it doesn't exist
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # If template already exists, we're done
    if template_path.exists():
        return
    
    print(f"📝 Creating default template: {template_name}")
    
    # Default template content
    template_content = """id: simple_chat_assistant
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
    description: The role or profession the assistant should embody (e.g., "helpful coding assistant", "data analyst", "technical writer")
  expertise:
    type: string
    required: false
    description: Optional specific area of expertise for this assistant (e.g., "Python programming and best practices", "data visualization", "API design")

metadata:
  tags: ["assistant", "chat", "general-purpose", "agent-framework"]
  author: "Dakora Examples"
  use_cases: ["agent configuration", "chat assistants", "system prompts", "microsoft-agent-framework"]
"""
    
    # Write the template file
    template_path.write_text(template_content)
    print(f"✅ Template created at: {template_path}")


def initialize_vault() -> Vault:
    """
    Initialize Dakora Vault for prompt template management.
    
    Returns:
        Vault: Configured Dakora Vault instance
        
    Raises:
        FileNotFoundError: If prompts directory doesn't exist
    """
    # Ensure the template exists before initializing vault
    setup_sample_templates("simple_chat_assistant")
    
    if not PROMPTS_DIR.exists():
        raise FileNotFoundError(
            f"Prompts directory not found: {PROMPTS_DIR}\n"
            "Run the setup script first: ./setup.ps1 or ./setup.sh"
        )
    
    # Initialize vault with prompts directory
    # Note: We skip the config file to avoid path issues when running from different directories
    return Vault(prompt_dir=str(PROMPTS_DIR))


def get_chat_client(api_key: str | None = None) -> AzureOpenAIChatClient:
    """
    Create Azure OpenAI chat client with appropriate authentication.
    
    Args:
        api_key: Optional API key. If not provided, uses Azure CLI authentication.
        
    Returns:
        AzureOpenAIChatClient: Configured chat client
    """
    if api_key:
        # Use API Key authentication
        print("🔑 Using API Key authentication")
        os.environ["AZURE_OPENAI_API_KEY"] = api_key
        return AzureOpenAIChatClient()
    else:
        # Use Azure CLI authentication (recommended)
        print("🔐 Using Azure CLI authentication")
        credential = AzureCliCredential()
        return AzureOpenAIChatClient(credential=credential)


async def main():
    """
    Main function demonstrating Dakora + Microsoft Agent Framework integration.
    
    This example shows:
    1. Loading environment configuration
    2. Initializing Dakora Vault for prompt management
    3. Rendering a prompt template with dynamic inputs
    4. Creating an Azure OpenAI agent with the rendered prompt
    5. Running a query against the agent
    """
    # Check required environment variable
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    if not endpoint:
        print("❌ Error: AZURE_OPENAI_ENDPOINT environment variable not set")
        print("\nPlease either:")
        print("1. Edit .env file and set AZURE_OPENAI_ENDPOINT")
        print("2. Or run: export AZURE_OPENAI_ENDPOINT='https://your-resource.openai.azure.com'")
        sys.exit(1)

    print(f"🌐 Using Azure OpenAI endpoint: {endpoint}\n")

    try:
        # Initialize Dakora Vault for prompt template management
        print("📚 Initializing Dakora Vault...")
        vault = initialize_vault()
        
        # Get a prompt template and render it with dynamic inputs
        # Using the simple_chat_assistant template with custom parameters
        print("📝 Loading and rendering prompt template...")
        template = vault.get("simple_chat_assistant")
        instructions = template.render(
            role="Helpful coding assistant",
            expertise="Python programming and best practices",
        )
        
        print(f"✅ Template rendered successfully\n")
        
        # Get authentication method
        api_key = os.environ.get("AZURE_OPENAI_API_KEY")
        chat_client = get_chat_client(api_key)
        
        # Create agent and run query
        print("🤖 Creating agent with rendered instructions...")
        async with chat_client.create_agent(
            instructions=instructions, 
            name="PythonAssistant"
        ) as agent:
            # Ask a question
            question = "How do I read a CSV file in Python?"
            print(f"\n� Question: {question}\n")
            
            result = await agent.run(question)
            print(f"🤖 Agent Response:\n{result.text}\n")
            
            print("✅ Example completed successfully!")
            
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
