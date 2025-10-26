"""Variant generation for prompt optimization."""

import asyncio
import re

from ..llm.provider import LLMProvider
from .types import Variant


class VariantGenerator:
    """Generates optimized prompt variants using different strategies."""

    def __init__(self, llm_provider: LLMProvider, model: str = "gpt-4o-mini"):
        """
        Initialize variant generator.

        Args:
            llm_provider: LLM provider for generating variants
            model: Model to use for generation (default: gpt-4o-mini)
        """
        self.llm = llm_provider
        self.model = model

    async def generate_variants(self, template: str) -> list[Variant]:
        """
        Generate 3 optimized variants of a prompt template sequentially.

        Each variant uses a different optimization strategy:
        - Clarity: Remove ambiguity, add structure, clearer instructions
        - Specificity: Add constraints, examples, output format guidance
        - Efficiency: Remove redundancy, tighter language, better token efficiency

        Args:
            template: Original template text

        Returns:
            List of 3 variant objects
        """
        strategies = [
            ("clarity", self._clarity_prompt()),
            ("specificity", self._specificity_prompt()),
            ("efficiency", self._efficiency_prompt()),
        ]

        variants = []
        for strategy, system_prompt in strategies:
            variant_template = await self._generate_variant(template, system_prompt)

            # Estimate token count (rough approximation)
            token_count = self._estimate_tokens(variant_template)

            variants.append(
                Variant(
                    template=variant_template,
                    strategy=strategy,
                    token_count=token_count,
                )
            )

        return variants

    async def generate_variants_parallel(self, template: str) -> list[Variant]:
        """
        Generate 3 optimized variants of a prompt template in parallel.

        This is 3x faster than sequential generation by running all LLM calls
        concurrently using asyncio.gather.

        Each variant uses a different optimization strategy:
        - Clarity: Remove ambiguity, add structure, clearer instructions
        - Specificity: Add constraints, examples, output format guidance
        - Efficiency: Remove redundancy, tighter language, better token efficiency

        Args:
            template: Original template text

        Returns:
            List of 3 variant objects
        """
        strategies = [
            ("clarity", self._clarity_prompt()),
            ("specificity", self._specificity_prompt()),
            ("efficiency", self._efficiency_prompt()),
        ]

        # Generate all variants in parallel
        tasks = [
            self._generate_variant(template, system_prompt)
            for _, system_prompt in strategies
        ]
        variant_templates = await asyncio.gather(*tasks)

        # Build variant objects
        variants = []
        for (strategy, _), variant_template in zip(strategies, variant_templates):
            token_count = self._estimate_tokens(variant_template)
            variants.append(
                Variant(
                    template=variant_template,
                    strategy=strategy,
                    token_count=token_count,
                )
            )

        return variants

    async def _generate_variant(self, template: str, system_prompt: str) -> str:
        """Generate a single variant using given system prompt."""
        # Combine system prompt and user message into single prompt
        full_prompt = f"""{system_prompt}

Original template:

{template}

Optimized template:"""

        response = await self.llm.execute(
            prompt=full_prompt,
            model=self.model,
            temperature=0.7,
            max_tokens=4000,
        )

        # Extract template from response (remove any markdown code blocks)
        optimized = response.content.strip()
        optimized = re.sub(r"^```(?:yaml|markdown)?\n", "", optimized)
        optimized = re.sub(r"\n```$", "", optimized)

        return optimized.strip()

    def _clarity_prompt(self) -> str:
        """System prompt for clarity-optimized variant."""
        return """You are an expert prompt engineer optimizing for CLARITY.

Your goal: Remove ambiguity, add structure, and make instructions crystal clear.

Rules:
1. Preserve ALL {{ variables }} exactly as they appear (same names, same syntax)
2. Preserve ALL {% include "parts/..." %} directives exactly as they appear
3. DO NOT change the core intent or domain context
4. Focus on:
   - Removing ambiguous language
   - Adding clear structure (numbering, sections)
   - Making instructions more explicit
   - Clarifying expected output format

Output ONLY the optimized template text, no explanations."""

    def _specificity_prompt(self) -> str:
        """System prompt for specificity-optimized variant."""
        return """You are an expert prompt engineer optimizing for SPECIFICITY.

Your goal: Add constraints, examples, and detailed output format guidance.

Rules:
1. Preserve ALL {{ variables }} exactly as they appear (same names, same syntax)
2. Preserve ALL {% include "parts/..." %} directives exactly as they appear
3. DO NOT change the core intent or domain context
4. Focus on:
   - Adding specific constraints and boundaries
   - Including concrete examples where helpful
   - Defining precise output format (e.g., JSON schema, field names)
   - Specifying edge case handling

Output ONLY the optimized template text, no explanations."""

    def _efficiency_prompt(self) -> str:
        """System prompt for efficiency-optimized variant."""
        return """You are an expert prompt engineer optimizing for EFFICIENCY.

Your goal: Remove redundancy and improve token efficiency while maintaining clarity.

Rules:
1. Preserve ALL {{ variables }} exactly as they appear (same names, same syntax)
2. Preserve ALL {% include "parts/..." %} directives exactly as they appear
3. DO NOT change the core intent or domain context
4. Focus on:
   - Removing redundant words and phrases
   - Using tighter, more concise language
   - Eliminating unnecessary elaboration
   - Maintaining clarity while reducing token count

Output ONLY the optimized template text, no explanations."""

    def _estimate_tokens(self, text: str) -> int:
        """
        Rough token count estimation.

        Uses approximation: ~4 characters per token for English text.
        This is good enough for comparison purposes.
        """
        return len(text) // 4