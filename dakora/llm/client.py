from __future__ import annotations
import time
import asyncio
from typing import Optional, Any, List
import litellm
from litellm import completion, acompletion
from litellm.exceptions import (
    AuthenticationError,
    RateLimitError as LiteLLMRateLimitError,
    APIError,
    Timeout,
    BadRequestError
)

from ..exceptions import APIKeyError, RateLimitError, ModelNotFoundError, LLMError
from .models import ExecutionResult, ComparisonResult

class LLMClient:
    def __init__(self):
        litellm.suppress_debug_info = True
        litellm.drop_params = True
        litellm.cache = None

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

    async def _execute_async(self, prompt: str, model: str, **kwargs: Any) -> ExecutionResult:
        start_time = time.time()

        # Create a copy of kwargs to avoid mutation issues in parallel execution
        kwargs_copy = dict(kwargs)
        timeout = kwargs_copy.pop("timeout", 120)

        params = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "timeout": timeout,
            **kwargs_copy
        }

        try:
            response = await acompletion(**params)
        except AuthenticationError as e:
            return ExecutionResult(
                output="",
                provider="unknown",
                model=model,
                tokens_in=0,
                tokens_out=0,
                cost_usd=0.0,
                latency_ms=int((time.time() - start_time) * 1000),
                error=f"Invalid or missing API key for model '{model}': {str(e)}"
            )
        except LiteLLMRateLimitError as e:
            return ExecutionResult(
                output="",
                provider="unknown",
                model=model,
                tokens_in=0,
                tokens_out=0,
                cost_usd=0.0,
                latency_ms=int((time.time() - start_time) * 1000),
                error=f"Rate limit exceeded for model '{model}': {str(e)}"
            )
        except BadRequestError as e:
            return ExecutionResult(
                output="",
                provider="unknown",
                model=model,
                tokens_in=0,
                tokens_out=0,
                cost_usd=0.0,
                latency_ms=int((time.time() - start_time) * 1000),
                error=f"Bad request for model '{model}': {str(e)}"
            )
        except Timeout as e:
            return ExecutionResult(
                output="",
                provider="unknown",
                model=model,
                tokens_in=0,
                tokens_out=0,
                cost_usd=0.0,
                latency_ms=int((time.time() - start_time) * 1000),
                error=f"Request timeout for model '{model}': {str(e)}"
            )
        except (APIError, Exception) as e:
            return ExecutionResult(
                output="",
                provider="unknown",
                model=model,
                tokens_in=0,
                tokens_out=0,
                cost_usd=0.0,
                latency_ms=int((time.time() - start_time) * 1000),
                error=f"Error executing model '{model}': {str(e)}"
            )

        latency_ms = int((time.time() - start_time) * 1000)

        message = response.choices[0].message
        output = message.content or ""
        finish_reason = response.choices[0].finish_reason if hasattr(response.choices[0], 'finish_reason') else None

        if not output and hasattr(message, 'refusal') and message.refusal:
            output = f"[REFUSAL] {message.refusal}"

        provider = response._hidden_params.get("custom_llm_provider", "unknown")
        tokens_in = response.usage.prompt_tokens if response.usage else 0
        tokens_out = response.usage.completion_tokens if response.usage else 0

        cost_usd = 0.0
        if hasattr(response, '_hidden_params') and 'response_cost' in response._hidden_params:
            cost_usd = float(response._hidden_params['response_cost'])

        if not output and finish_reason == 'length':
            return ExecutionResult(
                output="",
                provider=provider,
                model=model,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                cost_usd=cost_usd,
                latency_ms=latency_ms,
                error=f"Max tokens limit reached. Please increase max_tokens to see output."
            )

        return ExecutionResult(
            output=output,
            provider=provider,
            model=model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            error=f"⚠️ Response truncated - max_tokens limit reached" if finish_reason == 'length' and output else None
        )

    async def compare(self, prompt: str, models: List[str], **kwargs: Any) -> ComparisonResult:
        tasks = [self._execute_async(prompt, model, **kwargs) for model in models]
        results = await asyncio.gather(*tasks)

        total_cost_usd = sum(r.cost_usd for r in results if r.error is None)
        total_tokens_in = sum(r.tokens_in for r in results if r.error is None)
        total_tokens_out = sum(r.tokens_out for r in results if r.error is None)
        total_time_ms = max((r.latency_ms for r in results), default=0)
        successful_count = sum(1 for r in results if r.error is None)
        failed_count = sum(1 for r in results if r.error is not None)

        return ComparisonResult(
            results=results,
            total_cost_usd=total_cost_usd,
            total_tokens_in=total_tokens_in,
            total_tokens_out=total_tokens_out,
            total_time_ms=total_time_ms,
            successful_count=successful_count,
            failed_count=failed_count
        )
