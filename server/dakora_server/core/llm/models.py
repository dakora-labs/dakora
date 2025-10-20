from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field

class ExecutionResult(BaseModel):
    output: str = Field(description="LLM response text")
    provider: str = Field(description="Provider name (e.g., 'openai', 'anthropic')")
    model: str = Field(description="Model name (e.g., 'gpt-5', 'claude-3-opus')")
    tokens_in: int = Field(ge=0, description="Input token count")
    tokens_out: int = Field(ge=0, description="Output token count")
    cost_usd: float = Field(ge=0.0, description="Execution cost in USD")
    latency_ms: int = Field(ge=0, description="Response latency in milliseconds")
    error: Optional[str] = Field(default=None, description="Error message if execution failed")

class ComparisonResult(BaseModel):
    results: List[ExecutionResult] = Field(description="List of execution results, one per model")
    total_cost_usd: float = Field(ge=0.0, description="Total cost across all successful executions")
    total_tokens_in: int = Field(ge=0, description="Total input tokens across all executions")
    total_tokens_out: int = Field(ge=0, description="Total output tokens across all executions")
    total_time_ms: int = Field(ge=0, description="Maximum latency across all executions")
    successful_count: int = Field(ge=0, description="Number of successful executions")
    failed_count: int = Field(ge=0, description="Number of failed executions")