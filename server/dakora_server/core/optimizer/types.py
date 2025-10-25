"""Data models for the prompt optimization engine."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class OptimizationRequest(BaseModel):
    """Request to optimize a prompt template."""

    template: str
    """The original template text to optimize."""

    inputs: dict[str, dict] | None = None
    """Input specifications for the template."""

    test_cases: list[dict] | None = None
    """Optional test cases to evaluate variants against."""


class Insight(BaseModel):
    """A human-readable improvement insight."""

    category: Literal["clarity", "specificity", "efficiency"]
    """The type of improvement."""

    description: str
    """Human-readable explanation of the improvement."""

    impact: str
    """Concrete value/benefit (e.g., '15% fewer tokens', 'reduces parsing errors')."""


class Variant(BaseModel):
    """A generated optimization variant."""

    template: str
    """The optimized template text."""

    strategy: Literal["clarity", "specificity", "efficiency"]
    """The optimization strategy used to generate this variant."""

    token_count: int | None = None
    """Approximate token count of the variant."""


class VariantScore(BaseModel):
    """Evaluation score for a variant."""

    variant: Variant
    """The evaluated variant."""

    score: float = Field(ge=0.0, le=10.0)
    """Internal quality score (0-10), not shown to users."""

    insights: list[Insight] = []
    """Human-readable insights about this variant's improvements."""


class OptimizationResult(BaseModel):
    """Result of prompt optimization."""

    original_template: str
    """The original template text."""

    best_variant: Variant
    """The recommended optimized variant."""

    all_variants: list[Variant]
    """All generated variants (for power users)."""

    insights: list[Insight]
    """Key improvements in the best variant."""

    token_reduction_pct: float | None = None
    """Percentage reduction in tokens (if calculable)."""

    created_at: datetime = Field(default_factory=lambda: datetime.utcnow())
    """When this optimization was created."""