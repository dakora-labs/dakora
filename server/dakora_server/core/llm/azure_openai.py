"""Azure OpenAI provider implementation."""

import time
from typing import Any

from openai import AsyncAzureOpenAI

from .provider import ExecutionResult, ModelInfo
from ..token_pricing import get_pricing_service


class AzureOpenAIProvider:
    """Provider for Azure OpenAI."""

    # Model max tokens
    MAX_TOKENS = {
        "gpt-5-mini": 128000,
        "gpt-4o": 128000,
        "gpt-4o-mini": 128000,
        "gpt-4-turbo": 128000,
        "gpt-3.5-turbo": 16385,
    }

    def __init__(
        self,
        endpoint: str,
        api_key: str,
        deployment_name: str,
        api_version: str = "2024-12-01-preview",
    ):
        """Initialize Azure OpenAI provider.

        Args:
            endpoint: Azure OpenAI endpoint URL
            api_key: Azure OpenAI API key
            deployment_name: Default deployment name
            api_version: Azure OpenAI API version
        """
        self.endpoint = endpoint
        self.deployment_name = deployment_name
        self.client = AsyncAzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version=api_version,
        )

    async def execute(
        self, prompt: str, model: str | None = None, **kwargs: Any
    ) -> ExecutionResult:
        """Execute a prompt against Azure OpenAI.

        Args:
            prompt: The prompt text to execute
            model: The model ID to use (defaults to deployment_name)
            **kwargs: Additional parameters (temperature, max_tokens, etc.)

        Returns:
            ExecutionResult with content and metrics

        Raises:
            Exception: If execution fails
        """
        deployment = model or self.deployment_name
        start_time = time.time()

        try:
            # Call Azure OpenAI API
            response = await self.client.chat.completions.create(
                model=deployment,
                messages=[{"role": "user", "content": prompt}],
                **kwargs,
            )

            # Calculate latency
            latency_ms = int((time.time() - start_time) * 1000)

            # Extract token usage
            usage = response.usage
            if not usage:
                raise ValueError("No usage information in response")

            tokens_input = usage.prompt_tokens
            tokens_output = usage.completion_tokens
            tokens_total = usage.total_tokens

            # Calculate cost using centralized TokenPricingService when possible
            pricing_service = get_pricing_service()
            cost = pricing_service.calculate_cost(
                provider="azure_openai",
                model=deployment,
                tokens_in=tokens_input,
                tokens_out=tokens_output,
            )

            # If pricing is not available centrally, return None for cost_usd
            # so callers can decide how to handle unknown pricing.

            # Extract content
            content = response.choices[0].message.content or ""

            return ExecutionResult(
                content=content,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                tokens_total=tokens_total,
                cost_usd=(round(cost, 6) if cost is not None else None),
                latency_ms=latency_ms,
                model=deployment,
                provider="azure_openai",
            )

        except Exception as e:
            # Re-raise with context
            raise Exception(f"Azure OpenAI execution failed: {str(e)}") from e

    def get_available_models(self) -> list[ModelInfo]:
        """Get list of available models for Azure OpenAI.

        Returns:
            List of ModelInfo objects
        """
        models = []
        pricing_service = get_pricing_service()
        for model_id, max_tokens in self.MAX_TOKENS.items():
            svc_pricing = pricing_service.get_pricing("azure_openai", model_id)
            if svc_pricing:
                input_cost, output_cost = svc_pricing
            else:
                input_cost = None
                output_cost = None

            models.append(
                ModelInfo(
                    id=model_id,
                    name=self._format_model_name(model_id),
                    provider="azure_openai",
                    input_cost_per_1k=input_cost,
                    output_cost_per_1k=output_cost,
                    max_tokens=max_tokens,
                )
            )

        return models

    def _format_model_name(self, model_id: str) -> str:
        """Format model ID into display name."""
        name_map = {
            "gpt-4o": "GPT-4o",
            "gpt-4o-mini": "GPT-4o Mini",
            "gpt-4-turbo": "GPT-4 Turbo",
            "gpt-3.5-turbo": "GPT-3.5 Turbo",
        }
        return name_map.get(model_id, model_id.upper())