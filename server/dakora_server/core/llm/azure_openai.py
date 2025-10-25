"""Azure OpenAI provider implementation."""

import time
from typing import Any

from openai import AsyncAzureOpenAI

from .provider import ExecutionResult, LLMProvider, ModelInfo


class AzureOpenAIProvider:
    """Provider for Azure OpenAI."""

    # Model pricing (per 1K tokens)
    # Order matters: first model is used as default for optimization
    PRICING = {
        "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},  # Fast, cheap, good for optimization
        "gpt-4o": {"input": 0.0025, "output": 0.01},
        "gpt-5-mini": {"input": 0.000125, "output": 0.001},  # Reasoning model (slower)
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    }

    # Model max tokens
    MAX_TOKENS = {
        "gpt-4o-mini": 128000,
        "gpt-4o": 128000,
        "gpt-5-mini": 128000,
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

        # Convert max_tokens to max_completion_tokens for newer API versions
        if "max_tokens" in kwargs:
            kwargs["max_completion_tokens"] = kwargs.pop("max_tokens")

        # Filter out parameters not supported by reasoning models (o1, o3, etc.)
        # These models only support default temperature (1.0) and have other restrictions
        if self._is_reasoning_model(deployment):
            # Remove unsupported parameters for reasoning models
            kwargs.pop("temperature", None)
            kwargs.pop("top_p", None)
            kwargs.pop("presence_penalty", None)
            kwargs.pop("frequency_penalty", None)

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

            # Calculate cost
            pricing = self.PRICING.get(deployment, self.PRICING["gpt-4o"])
            cost_usd = (
                tokens_input / 1000 * pricing["input"]
                + tokens_output / 1000 * pricing["output"]
            )

            # Extract content
            content = response.choices[0].message.content or ""

            return ExecutionResult(
                content=content,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                tokens_total=tokens_total,
                cost_usd=round(cost_usd, 6),
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
        for model_id, pricing in self.PRICING.items():
            models.append(
                ModelInfo(
                    id=model_id,
                    name=self._format_model_name(model_id),
                    provider="azure_openai",
                    input_cost_per_1k=pricing["input"],
                    output_cost_per_1k=pricing["output"],
                    max_tokens=self.MAX_TOKENS.get(model_id, 128000),
                )
            )
        return models

    def list_models(self) -> list[ModelInfo]:
        """Alias for get_available_models() for compatibility.

        Returns:
            List of ModelInfo objects
        """
        return self.get_available_models()

    def _is_reasoning_model(self, model: str) -> bool:
        """Check if model is a reasoning model (o1, o3, gpt-5, etc.) with restricted parameters.

        Args:
            model: Model ID to check

        Returns:
            True if model is a reasoning model, False otherwise
        """
        reasoning_prefixes = ("o1", "o3", "o4", "gpt-5")
        return any(model.startswith(prefix) for prefix in reasoning_prefixes)

    def _format_model_name(self, model_id: str) -> str:
        """Format model ID into display name."""
        name_map = {
            "gpt-4o": "GPT-4o",
            "gpt-4o-mini": "GPT-4o Mini",
            "gpt-4-turbo": "GPT-4 Turbo",
            "gpt-3.5-turbo": "GPT-3.5 Turbo",
        }
        return name_map.get(model_id, model_id.upper())