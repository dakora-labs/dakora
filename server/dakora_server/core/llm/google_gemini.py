"""Google Gemini provider implementation."""

import time
from typing import Any

import google.generativeai as genai

from .provider import ExecutionResult, ModelInfo
from ..token_pricing import get_pricing_service


class GoogleGeminiProvider:
    """Provider for Google Gemini."""

    # Pricing is centralized in TokenPricingService; providers do not keep local pricing.

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

            # Prefer centralized TokenPricingService for cost calculation
            pricing_service = get_pricing_service()
            cost = pricing_service.calculate_cost(
                provider="google",
                model=model,
                tokens_in=tokens_input,
                tokens_out=tokens_output,
            )

            # If no centralized pricing is found, return cost=None to indicate unknown
            # (upstream callers can decide how to display or charge for unknown costs).

            # Extract content
            content = response.text

            return ExecutionResult(
                content=content,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                tokens_total=tokens_total,
                cost_usd=(round(cost, 6) if cost is not None else None),
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
        pricing_service = get_pricing_service()

        # Query pricing table keys for known models by asking the pricing service
        # The TokenPricingService currently stores known models; iterate through
        # the tokens in MAX_TOKENS as the authoritative model list for this provider.
        for model_id, max_tokens in self.MAX_TOKENS.items():
            svc_pricing = pricing_service.get_pricing("google", model_id)
            if svc_pricing:
                input_cost, output_cost = svc_pricing
            else:
                input_cost = None
                output_cost = None

            models.append(
                ModelInfo(
                    id=model_id,
                    name=self._format_model_name(model_id),
                    provider="google_gemini",
                    input_cost_per_1k=input_cost,
                    output_cost_per_1k=output_cost,
                    max_tokens=max_tokens,
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