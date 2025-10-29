#!/usr/bin/env python3
"""
Test script for Microsoft Agent Framework (MAF) with Azure OpenAI Chat API.
Configuration is loaded from .env file.
"""
import os
import asyncio
import logging
from dotenv import load_dotenv
from agent_framework.azure import AzureOpenAIChatClient
from dakora_client import Dakora
from dakora_agents.maf import DakoraIntegration

# Enable debug logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logging.getLogger('dakora_agents').setLevel(logging.DEBUG)
logging.getLogger('opentelemetry').setLevel(logging.WARNING)

async def main():
    # Load environment variables from .env file
    load_dotenv()
    dakora = Dakora(base_url="https://dakora-api.onrender.com")

    # One-line OTEL setup with Dakora integration
    middleware = DakoraIntegration.setup(dakora)

    # Render a prompt template from Dakora (returns a RenderResult)
    instructions_result = await dakora.prompts.render("haiku_agent", {})
    question_prompt = await dakora.prompts.render("simple_question", {})

    # Get configuration from environment variables
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    deployment_name = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")

    print("Using API key authentication")
    client = AzureOpenAIChatClient(
        endpoint=endpoint,
        deployment_name=deployment_name,
        api_version=api_version,
        api_key=api_key,
        middleware=[middleware],
    )

    # Create an agent with template text and agent ID
    agent = client.create_agent(
        id="haiku-bot-v1",
        name="HaikuBot",
        instructions=instructions_result.text,  # Use .text property
    )
    print("\n" + "="*50)
    print("Testing Microsoft Agent Framework (Chat API)")
    print("="*50 + "\n")

    try:
        # Run a test prompt
        response = await agent.run(question_prompt.to_message())
        print(response)
        print("\n" + "="*50 + "\n")
    finally:
        # Properly cleanup: close the HTTP client which waits for pending requests
        await dakora.close()
        print("Dakora client closed gracefully.")


if __name__ == "__main__":
    asyncio.run(main())