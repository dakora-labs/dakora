"""LLM provider protocol and data models."""

from dataclasses import dataclass
from typing import Any, Protocol, Optional


@dataclass
class ExecutionResult:
    """Result from executing a prompt against an LLM."""

    content: str
    tokens_input: int
    tokens_output: int
    tokens_total: int
    cost_usd: Optional[float]
    latency_ms: int
    model: str
    provider: str


@dataclass
class ModelInfo:
    """Information about an available LLM model."""

    id: str  # "gpt-4o", "claude-3-5-sonnet"
    name: str  # "GPT-4o"
    provider: str  # "azure_openai", "anthropic"
    input_cost_per_1k: Optional[float]
    output_cost_per_1k: Optional[float]
    max_tokens: int


class LLMProvider(Protocol):
    """Protocol for LLM providers."""

    async def execute(
        self, prompt: str, model: str, **kwargs: Any
    ) -> ExecutionResult:
        """Execute a prompt against the LLM.

        Args:
            prompt: The prompt text to execute
            model: The model ID to use
            **kwargs: Additional provider-specific parameters

        Returns:
            ExecutionResult with content and metrics

        Raises:
            Exception: If execution fails
        """
        ...

    def get_available_models(self) -> list[ModelInfo]:
        """Get list of available models for this provider.

        Returns:
            List of ModelInfo objects
        """
        ...