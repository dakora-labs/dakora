"""Generate human-readable explanations of prompt improvements."""

import json

from ..llm.provider import LLMProvider
from .types import Insight, Variant


class ImprovementExplainer:
    """Generates human-readable explanations of prompt improvements."""

    def __init__(self, llm_provider: LLMProvider, model: str = "gpt-4o-mini"):
        """
        Initialize improvement explainer.

        Args:
            llm_provider: LLM provider for generating explanations
            model: Model to use for explanations (default: gpt-4o-mini)
        """
        self.llm = llm_provider
        self.model = model

    async def explain_improvements(
        self,
        original_template: str,
        best_variant: Variant,
        all_insights: list[Insight],
    ) -> list[Insight]:
        """
        Generate consolidated, human-readable improvement insights.

        Takes all insights from variant evaluation and consolidates them
        into clear, actionable explanations for the user.

        Args:
            original_template: Original template text
            best_variant: The best/recommended variant
            all_insights: All insights from evaluation

        Returns:
            Consolidated list of top insights (max 5)
        """
        # If we already have good insights from evaluation, enhance them
        if all_insights:
            return await self._enhance_insights(
                original_template, best_variant, all_insights
            )

        # Otherwise generate fresh insights
        return await self._generate_insights(original_template, best_variant)

    async def _enhance_insights(
        self,
        original_template: str,
        best_variant: Variant,
        insights: list[Insight],
    ) -> list[Insight]:
        """
        Enhance existing insights with better descriptions and impact statements.

        Args:
            original_template: Original template
            best_variant: Best variant
            insights: Existing insights to enhance

        Returns:
            Enhanced insights
        """
        # For now, just filter and return top insights
        # Could enhance with LLM in future if needed
        return insights[:5]  # Max 5 insights for UI

    async def _generate_insights(
        self,
        original_template: str,
        best_variant: Variant,
    ) -> list[Insight]:
        """
        Generate fresh insights about improvements.

        Args:
            original_template: Original template
            best_variant: Best variant

        Returns:
            List of insights
        """
        prompt = f"""You are an expert at explaining prompt engineering improvements in clear, human language.

Compare the original and optimized prompts. Identify the TOP 3-5 most impactful improvements.

For each improvement, explain:
1. WHAT changed (be specific)
2. WHY it's better (concrete benefit)
3. IMPACT on results (e.g., "reduces parsing errors", "15% more concise")

Return JSON:
{{
  "insights": [
    {{
      "category": "clarity" | "specificity" | "efficiency",
      "description": "Clear description of what improved",
      "impact": "Concrete benefit (measurable when possible)"
    }}
  ]
}}

Focus on improvements that matter to end-users. Avoid jargon.

Original:
{original_template}

Optimized ({best_variant.strategy}):
{best_variant.template}

Analysis (JSON only):"""

        response = await self.llm.execute(
            prompt=prompt,
            model=self.model,
            temperature=0.5,
            max_tokens=1000,
        )

        try:
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            data = json.loads(content)

            insights = [
                Insight(
                    category=item.get("category", "clarity"),
                    description=item.get("description", ""),
                    impact=item.get("impact", ""),
                )
                for item in data.get("insights", [])
            ]

            return insights[:5]  # Max 5 insights

        except (json.JSONDecodeError, IndexError, KeyError):
            # Fallback to empty list
            return []