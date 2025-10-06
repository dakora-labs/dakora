from __future__ import annotations
import time
from typing import Optional, Any
import litellm
from litellm import completion
from litellm.exceptions import (
    AuthenticationError,
    RateLimitError as LiteLLMRateLimitError,
    APIError,
    Timeout,
    BadRequestError
)

from ..exceptions import APIKeyError, RateLimitError, ModelNotFoundError, LLMError
from .models import ExecutionResult

class LLMClient:
    def __init__(self):
        litellm.suppress_debug_info = True
        litellm.drop_params = True

    def execute(self, prompt: str, model: str, **kwargs: Any) -> ExecutionResult:
        start_time = time.time()

        params = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "timeout": kwargs.pop("timeout", 120),
            **kwargs
        }

        try:
            response = completion(**params)
        except AuthenticationError as e:
            raise APIKeyError(f"Invalid or missing API key for model '{model}': {str(e)}") from e
        except LiteLLMRateLimitError as e:
            raise RateLimitError(f"Rate limit exceeded for model '{model}': {str(e)}") from e
        except BadRequestError as e:
            if "model" in str(e).lower() or "not found" in str(e).lower():
                raise ModelNotFoundError(f"Model '{model}' not found or not available: {str(e)}") from e
            raise LLMError(f"Bad request for model '{model}': {str(e)}") from e
        except Timeout as e:
            raise LLMError(f"Request timeout for model '{model}': {str(e)}") from e
        except APIError as e:
            raise LLMError(f"API error for model '{model}': {str(e)}") from e
        except Exception as e:
            raise LLMError(f"Unexpected error executing model '{model}': {str(e)}") from e

        latency_ms = int((time.time() - start_time) * 1000)

        output = response.choices[0].message.content or ""
        provider = response._hidden_params.get("custom_llm_provider", "unknown")
        tokens_in = response.usage.prompt_tokens if response.usage else 0
        tokens_out = response.usage.completion_tokens if response.usage else 0

        cost_usd = 0.0
        if hasattr(response, '_hidden_params') and 'response_cost' in response._hidden_params:
            cost_usd = float(response._hidden_params['response_cost'])

        return ExecutionResult(
            output=output,
            provider=provider,
            model=model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost_usd,
            latency_ms=latency_ms
        )
