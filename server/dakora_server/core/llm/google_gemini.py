"""Google Gemini provider implementation."""

import time
from typing import Any

import google.generativeai as genai

from .provider import ExecutionResult, ModelInfo


class GoogleGeminiProvider:
    """Provider for Google Gemini."""

    # Model pricing (per 1K tokens)
    # Source: https://ai.google.dev/gemini-api/docs/pricing
    PRICING = {
        "gemini-2.5-pro": {
            # Tiered pricing based on prompt token count
            "input_low": 0.00125,  # $1.25 per 1M tokens (prompts <= 200k tokens)
            "input_high": 0.0025,  # $2.50 per 1M tokens (prompts > 200k tokens)
            "output_low": 0.01,  # $10.00 per 1M tokens (prompts <= 200k tokens)
            "output_high": 0.015,  # $15.00 per 1M tokens (prompts > 200k tokens)
            "tier_threshold": 200000,  # 200k tokens
        },
        "gemini-2.5-flash": {
            "input": 0.0003,  # $0.30 per 1M tokens (text)
            "output": 0.0025,  # $2.50 per 1M tokens
        },
    }

    # Model max tokens (context window)
    MAX_TOKENS = {
        "gemini-2.5-pro": 1048576,  # 1M tokens
        "gemini-2.5-flash": 1048576,  # 1M tokens
    }

    def __init__(self, api_key: str):
        """Initialize Google Gemini provider.

        Args:
            api_key: Google Gemini API key
        """
        self.api_key = api_key
        genai.configure(api_key=api_key)

    async def execute(
        self, prompt: str, model: str | None = None, **kwargs: Any
    ) -> ExecutionResult:
        """Execute a prompt against Google Gemini.

        Args:
            prompt: The prompt text to execute
            model: The model ID to use (required)
            **kwargs: Additional parameters (temperature, max_tokens, etc.)

        Returns:
            ExecutionResult with content and metrics

        Raises:
            ValueError: If model is not specified
            Exception: If execution fails
        """
        if not model:
            raise ValueError("model parameter is required for GoogleGeminiProvider")

        start_time = time.time()

        try:
            # Create generative model
            gemini_model = genai.GenerativeModel(model)

            # Extract generation config from kwargs
            generation_config = {}
            if "temperature" in kwargs:
                generation_config["temperature"] = kwargs["temperature"]
            if "max_tokens" in kwargs:
                generation_config["max_output_tokens"] = kwargs["max_tokens"]

            # Generate content
            response = await gemini_model.generate_content_async(
                prompt,
                generation_config=generation_config if generation_config else None,
            )

            # Calculate latency
            latency_ms = int((time.time() - start_time) * 1000)

            # Extract token usage
            if not response.usage_metadata:
                raise ValueError("No usage information in response")

            tokens_input = response.usage_metadata.prompt_token_count
            tokens_output = response.usage_metadata.candidates_token_count
            tokens_total = response.usage_metadata.total_token_count

            # Calculate cost with tiered pricing for gemini-2.5-pro
            pricing = self.PRICING.get(model, self.PRICING["gemini-2.5-flash"])

            if "tier_threshold" in pricing:
                # Tiered pricing (gemini-2.5-pro)
                if tokens_input > pricing["tier_threshold"]:
                    input_cost_per_1k = pricing["input_high"]
                    output_cost_per_1k = pricing["output_high"]
                else:
                    input_cost_per_1k = pricing["input_low"]
                    output_cost_per_1k = pricing["output_low"]
            else:
                # Flat pricing (gemini-2.5-flash)
                input_cost_per_1k = pricing["input"]
                output_cost_per_1k = pricing["output"]

            cost_usd = (
                tokens_input / 1000 * input_cost_per_1k
                + tokens_output / 1000 * output_cost_per_1k
            )

            # Extract content
            content = response.text

            return ExecutionResult(
                content=content,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                tokens_total=tokens_total,
                cost_usd=round(cost_usd, 6),
                latency_ms=latency_ms,
                model=model,
                provider="google_gemini",
            )

        except Exception as e:
            # Re-raise with context
            raise Exception(f"Google Gemini execution failed: {str(e)}") from e

    def get_available_models(self) -> list[ModelInfo]:
        """Get list of available models for Google Gemini.

        Returns:
            List of ModelInfo objects with base pricing (lower tier for tiered models)
        """
        models = []
        for model_id, pricing in self.PRICING.items():
            # Use lower tier pricing for display (most common case)
            if "tier_threshold" in pricing:
                input_cost = pricing["input_low"]
                output_cost = pricing["output_low"]
            else:
                input_cost = pricing["input"]
                output_cost = pricing["output"]

            models.append(
                ModelInfo(
                    id=model_id,
                    name=self._format_model_name(model_id),
                    provider="google_gemini",
                    input_cost_per_1k=input_cost,
                    output_cost_per_1k=output_cost,
                    max_tokens=self.MAX_TOKENS.get(model_id, 1048576),
                )
            )
        return models

    def _format_model_name(self, model_id: str) -> str:
        """Format model ID into display name."""
        name_map = {
            "gemini-2.5-pro": "Gemini 2.5 Pro",
            "gemini-2.5-flash": "Gemini 2.5 Flash",
        }
        return name_map.get(model_id, model_id)