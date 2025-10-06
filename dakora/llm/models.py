from __future__ import annotations
from pydantic import BaseModel, Field

class ExecutionResult(BaseModel):
    output: str = Field(description="LLM response text")
    provider: str = Field(description="Provider name (e.g., 'openai', 'anthropic')")
    model: str = Field(description="Model name (e.g., 'gpt-5', 'claude-3-opus')")
    tokens_in: int = Field(ge=0, description="Input token count")
    tokens_out: int = Field(ge=0, description="Output token count")
    cost_usd: float = Field(ge=0.0, description="Execution cost in USD")
    latency_ms: int = Field(ge=0, description="Response latency in milliseconds")