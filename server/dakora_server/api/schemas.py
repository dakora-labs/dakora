"""API request/response schemas"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field


class RenderRequest(BaseModel):
    inputs: Dict[str, Any] = Field(default_factory=dict)
    resolve_includes_only: bool = Field(default=False, description="If True, only resolve {% include %} directives but leave {{ variables }} as-is")


class CreateTemplateRequest(BaseModel):
    id: str
    version: str = "1.0.0"
    description: Optional[str] = None
    template: str
    inputs: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class UpdateTemplateRequest(BaseModel):
    version: Optional[str] = None
    description: Optional[str] = None
    template: Optional[str] = None
    inputs: Optional[Dict[str, Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None


class TemplateResponse(BaseModel):
    id: str
    version: str
    description: Optional[str]
    template: str
    inputs: Dict[str, Any]
    metadata: Dict[str, Any]


class RenderResponse(BaseModel):
    rendered: str
    inputs_used: Dict[str, Any]

class TemplateUsage(BaseModel):
    """Information about a template used in an execution"""
    prompt_id: str
    version: str
    inputs: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None


class ExecutionCreate(BaseModel):
    """Request to create an execution log entry"""
    trace_id: str
    parent_trace_id: Optional[str] = None
    session_id: str
    agent_id: Optional[str] = None
    template_usages: Optional[List[TemplateUsage]] = None
    conversation_history: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    latency_ms: Optional[int] = None
    cost_usd: Optional[float] = None


class ExecutionResponse(BaseModel):
    """Response after creating an execution log"""
    trace_id: str
    status: str = "logged"


class ExecuteRequest(BaseModel):
    inputs: Dict[str, Any] = Field(default_factory=dict)
    model: Optional[str] = Field(default=None, description="Model to use (defaults to workspace default)")
    provider: Optional[str] = Field(default=None, description="Provider to use (defaults to workspace provider)")


class ExecutionMetrics(BaseModel):
    tokens_input: int
    tokens_output: int
    tokens_total: int
    cost_usd: float
    latency_ms: int


class ExecuteResponse(BaseModel):
    execution_id: str
    content: str
    metrics: ExecutionMetrics
    model: str
    provider: str
    created_at: str


class ModelInfo(BaseModel):
    id: str
    name: str
    provider: str
    input_cost_per_1k: float
    output_cost_per_1k: float
    max_tokens: int


class ModelsResponse(BaseModel):
    models: List[ModelInfo]
    default_model: Optional[str] = None


class ExecutionRecord(BaseModel):
    execution_id: str
    prompt_id: str
    version: str
    inputs: Dict[str, Any]
    model: str
    provider: str
    output_text: Optional[str]
    error_message: Optional[str]
    status: str
    metrics: Optional[ExecutionMetrics]
    created_at: str


class ExecutionsResponse(BaseModel):
    executions: List[ExecutionRecord]
    total: int


# Optimization schemas

class OptimizePromptRequest(BaseModel):
    """Request to optimize a prompt template."""
    test_cases: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Optional test cases for evaluation. If not provided, synthetic cases will be generated.",
    )


class OptimizationInsight(BaseModel):
    """A human-readable insight about an optimization improvement."""
    category: str = Field(description="Category of improvement (e.g., 'clarity', 'specificity', 'efficiency')")
    description: str = Field(description="Human-readable description of the improvement")
    impact: str = Field(description="Expected impact (e.g., 'reduces ambiguity', 'improves output quality')")


class OptimizePromptResponse(BaseModel):
    """Response from prompt optimization."""
    optimization_id: str = Field(description="Unique ID for this optimization run")
    original_template: str = Field(description="Original template text")
    optimized_template: str = Field(description="Optimized template text")
    insights: List[OptimizationInsight] = Field(description="List of improvements made")
    token_reduction_pct: Optional[float] = Field(description="Percentage reduction in tokens (negative if increased)")
    created_at: str = Field(description="ISO timestamp of optimization")


class OptimizationRunRecord(BaseModel):
    """Record of a past optimization run."""
    optimization_id: str
    prompt_id: str
    version: str
    original_template: str
    optimized_template: str
    insights: List[OptimizationInsight]
    token_reduction_pct: Optional[float]
    applied: bool = Field(description="Whether this optimization was applied to create a new prompt version")
    created_at: str


class OptimizationRunsResponse(BaseModel):
    """List of optimization runs for a prompt."""
    optimization_runs: List[OptimizationRunRecord]
    total: int


class QuotaInfo(BaseModel):
    """Workspace quota information."""
    tier: str = Field(description="Quota tier (e.g., 'free', 'starter', 'pro')")
    optimizations_used: int = Field(description="Number of optimizations used this month")
    optimizations_limit: int = Field(description="Maximum optimizations allowed this month")
    optimizations_remaining: int = Field(description="Remaining optimizations this month")
    usage_percentage: float = Field(description="Usage as a percentage (0-100)")
    period_start: str = Field(description="ISO timestamp of current billing period start")
    period_end: str = Field(description="ISO timestamp of current billing period end")