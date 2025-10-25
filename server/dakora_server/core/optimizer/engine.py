"""Main orchestrator for prompt optimization."""

import asyncio

from ..llm.provider import LLMProvider
from .evaluator import VariantEvaluator
from .explainer import ImprovementExplainer
from .generator import VariantGenerator
from .types import OptimizationRequest, OptimizationResult, Variant, VariantScore


class OptimizationEngine:
    """Orchestrates the complete prompt optimization process."""

    def __init__(self, llm_provider: LLMProvider, model: str = "gpt-4o-mini"):
        """
        Initialize optimization engine.

        Args:
            llm_provider: LLM provider for all optimization operations
            model: Model to use for optimization (default: gpt-4o-mini)
        """
        self.llm = llm_provider
        self.model = model
        self.generator = VariantGenerator(llm_provider, model)
        self.evaluator = VariantEvaluator(llm_provider, model)
        self.explainer = ImprovementExplainer(llm_provider, model)

    async def optimize(self, request: OptimizationRequest) -> OptimizationResult:
        """
        Optimize a prompt template.

        Process:
        1. Generate 3 variants in parallel (clarity, specificity, efficiency)
        2. Generate test cases once (if not provided)
        3. Evaluate all variants in parallel with LLM critic
        4. Select best variant based on score
        5. Generate human-readable insights
        6. Return result with best variant and alternatives

        Args:
            request: Optimization request with template and optional test cases

        Returns:
            Optimization result with best variant and insights
        """
        # Step 1: Generate variants in parallel (3x faster)
        variants = await self.generator.generate_variants_parallel(request.template)

        # Step 2: Generate test cases once if not provided
        test_cases = request.test_cases
        if not test_cases:
            test_cases = await self.evaluator.generate_test_cases(request.template)

        # Step 3: Evaluate all variants in parallel (3x faster)
        evaluation_tasks = [
            self.evaluator.evaluate_variant(
                original_template=request.template,
                variant=variant,
                test_cases=test_cases,
            )
            for variant in variants
        ]
        scored_variants: list[VariantScore] = await asyncio.gather(*evaluation_tasks)

        # Step 4: Select best variant (highest score)
        best_scored = max(scored_variants, key=lambda s: s.score)
        best_variant = best_scored.variant

        # Step 5: Collect all insights from best variant
        all_insights = best_scored.insights

        # Step 6: Generate/enhance human-readable explanations
        final_insights = await self.explainer.explain_improvements(
            original_template=request.template,
            best_variant=best_variant,
            all_insights=all_insights,
        )

        # Step 7: Calculate token reduction percentage
        original_tokens = self._estimate_tokens(request.template)
        optimized_tokens = best_variant.token_count or 0
        token_reduction_pct = None
        if original_tokens > 0 and optimized_tokens > 0:
            token_reduction_pct = (
                (original_tokens - optimized_tokens) / original_tokens
            ) * 100

        # Step 8: Build result
        return OptimizationResult(
            original_template=request.template,
            best_variant=best_variant,
            all_variants=variants,
            insights=final_insights,
            token_reduction_pct=token_reduction_pct,
        )

    def _estimate_tokens(self, text: str) -> int:
        """Rough token count estimation (~4 chars per token)."""
        return len(text) // 4