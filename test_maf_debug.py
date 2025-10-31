#!/usr/bin/env python3
"""
Minimal example of Microsoft Agent Framework (MAF) with Dakora integration.
Configuration is loaded from .env file.
"""
import os
import asyncio
from dotenv import load_dotenv
from agent_framework.azure import AzureOpenAIChatClient
from dakora_client import Dakora
from dakora_agents.maf import DakoraIntegration


async def main():
    # Load environment variables
    load_dotenv()

    # Initialize Dakora client
    dakora = Dakora(base_url="http://localhost:8000")

    # Setup OTEL integration (one line!)
    middleware = DakoraIntegration.setup(dakora)

    # Render a prompt template from Dakora (returns a RenderResult)
    instructions_result = await dakora.prompts.render("haiku_agent", {})
    question_prompt = await dakora.prompts.render("simple_question", {})

    # Get Azure OpenAI configuration from environment
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    deployment_name = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")

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