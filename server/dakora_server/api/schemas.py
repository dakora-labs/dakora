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
    version_number: Optional[int] = Field(default=None, description="Auto-incrementing version number from versioning system")
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
    role: Optional[str] = None
    source: Optional[str] = None
    message_index: Optional[int] = None


class ExecutionCreate(BaseModel):
    """Request to create an execution log entry"""
    trace_id: str
    parent_trace_id: Optional[str] = None
    session_id: str
    agent_id: Optional[str] = None
    source: Optional[str] = None
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


class ExecutionListItem(BaseModel):
    """Summary information for a recorded execution trace."""
    trace_id: str
    parent_trace_id: Optional[str] = None
    session_id: Optional[str] = None
    agent_id: Optional[str] = None
    source: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    total_tokens_in: Optional[int] = None  # Aggregated across all spans in trace
    total_tokens_out: Optional[int] = None  # Aggregated across all spans in trace
    cost_usd: Optional[float] = None
    latency_ms: Optional[int] = None
    created_at: Optional[str] = None
    template_count: int = 0
    metadata: Optional[Dict[str, Any]] = None
    # New fields for Priority 1 UI improvements
    span_count: int = 0
    span_type_breakdown: Optional[Dict[str, int]] = None  # e.g., {"agent": 1, "chat": 2, "tool": 1}
    has_errors: bool = False
    error_message: Optional[str] = None
    # Multi-agent/model detection
    unique_agents: Optional[List[str]] = None  # List of unique agent names in this execution
    unique_models: Optional[List[str]] = None  # List of unique models used in this execution


class ExecutionListResponse(BaseModel):
    """Paginated execution list response."""
    executions: List[ExecutionListItem]
    total: int
    limit: int
    offset: int


class ExecuteRequest(BaseModel):
    inputs: Dict[str, Any] = Field(default_factory=dict)
    model: Optional[str] = Field(default=None, description="Model to use (defaults to workspace default)")
    provider: Optional[str] = Field(default=None, description="Provider to use (defaults to workspace provider)")


class ExecutionMetrics(BaseModel):
    tokens_input: int
    tokens_output: int
    tokens_total: int
    # cost may be unknown for some executions/providers; allow None
    cost_usd: Optional[float]
    latency_ms: int


class ExecuteResponse(BaseModel):
    execution_id: str
    trace_id: Optional[str] = Field(
        default=None,
        description="Trace identifier when execution is logged to observability",
    )
    content: str
    metrics: ExecutionMetrics
    model: str
    provider: str
    created_at: str


class ModelInfo(BaseModel):
    id: str
    name: str
    provider: str
    # pricing may be unknown for some providers; allow None
    input_cost_per_1k: Optional[float]
    output_cost_per_1k: Optional[float]
    max_tokens: int


class ModelsResponse(BaseModel):
    models: List[ModelInfo]
    default_model: Optional[str] = None


class ExecutionRecord(BaseModel):
    execution_id: str
    prompt_id: str
    version: str
    trace_id: Optional[str] = None
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


# Version schemas

class VersionHistoryItem(BaseModel):
    """Single version record in version history."""
    version: int = Field(description="Version number")
    content_hash: str = Field(description="SHA256 hash of version content")
    created_at: str = Field(description="ISO timestamp of version creation")
    created_by: str = Field(description="User ID who created this version")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Version metadata")


class VersionHistoryResponse(BaseModel):
    """List of all versions for a prompt."""
    versions: List[VersionHistoryItem]


class RollbackRequest(BaseModel):
    """Request to rollback prompt to a specific version."""
    version: int = Field(description="Version number to rollback to", gt=0)


# New execution schemas for OTLP-native observability

class MessagePart(BaseModel):
    """A part of a message (text, image, etc.)"""
    type: str = Field(description="Part type (text, image_url, etc.)")
    content: str = Field(description="Content of the part")


class Message(BaseModel):
    """A single message in a conversation"""
    role: str = Field(description="Message role (system, user, assistant, tool)")
    parts: List[MessagePart] = Field(description="Message parts/content")
    msg_index: int = Field(description="Message index within direction")
    finish_reason: Optional[str] = Field(default=None, description="Finish reason (for output messages)")


class ChildSpan(BaseModel):
    """Summary of a child execution span"""
    span_id: str
    type: str
    agent_name: Optional[str] = None
    latency_ms: Optional[int] = None
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    status: Optional[str] = None


class TemplateInfo(BaseModel):
    """Template linkage information"""
    prompt_id: str
    version: str
    inputs: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None


class ExecutionDetailResponse(BaseModel):
    """Detailed execution with messages and hierarchy"""
    trace_id: str
    span_id: str
    type: str
    agent_name: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    start_time: str
    latency_ms: Optional[int] = None
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    total_cost_usd: Optional[float] = None
    status: Optional[str] = None
    status_message: Optional[str] = None
    
    # Messages
    input_messages: List[Message] = Field(default_factory=list)
    output_messages: List[Message] = Field(default_factory=list)
    
    # Hierarchy
    child_spans: List[ChildSpan] = Field(default_factory=list)
    
    # Template linkage
    template_info: Optional[TemplateInfo] = None
    
    # Raw attributes
    attributes: Dict[str, Any] = Field(default_factory=dict)


class SpanTreeNode(BaseModel):
    """A node in the span hierarchy tree"""
    span_id: str
    parent_span_id: Optional[str] = None
    type: str
    agent_name: Optional[str] = None
    latency_ms: Optional[int] = None
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    depth: int
    start_time: str


class HierarchyResponse(BaseModel):
    """Full span hierarchy for a trace"""
    trace_id: str
    spans: List[SpanTreeNode]
