"""Variant evaluation for prompt optimization."""

import json
from typing import Any

from ..llm.provider import LLMProvider
from .types import Variant, VariantScore, Insight


class VariantEvaluator:
    """Evaluates prompt variants to determine quality."""

    def __init__(self, llm_provider: LLMProvider, model: str = "gpt-4o-mini"):
        """
        Initialize variant evaluator.

        Args:
            llm_provider: LLM provider for evaluation
            model: Model to use for evaluation (default: gpt-4o-mini)
        """
        self.llm = llm_provider
        self.model = model

    async def evaluate_variant(
        self,
        original_template: str,
        variant: Variant,
        test_cases: list[dict] | None = None,
    ) -> VariantScore:
        """
        Evaluate a variant against the original template.

        Args:
            original_template: The original template text
            variant: The variant to evaluate
            test_cases: Test cases to use for evaluation (required)

        Returns:
            Variant score with quality metrics and insights
        """
        # Test cases should always be provided when calling this method
        # to avoid redundant generation in the optimization loop
        if not test_cases:
            test_cases = []

        # Use LLM as critic to evaluate variant
        evaluation = await self._evaluate_with_llm(
            original_template, variant, test_cases
        )

        return VariantScore(
            variant=variant,
            score=evaluation["score"],
            insights=evaluation["insights"],
        )

    async def generate_test_cases(
        self, template: str, num_cases: int = 3
    ) -> list[dict]:
        """
        Generate synthetic test cases for a template.

        This is a public method that should be called once before evaluating
        multiple variants to avoid redundant test case generation.

        Args:
            template: Template to generate test cases for
            num_cases: Number of test cases to generate

        Returns:
            List of test case dictionaries
        """
        return await self._generate_synthetic_test_cases(template, num_cases)

    async def _generate_synthetic_test_cases(
        self, template: str, num_cases: int = 3
    ) -> list[dict]:
        """
        Generate synthetic test cases for a template.

        Args:
            template: Template to generate test cases for
            num_cases: Number of test cases to generate

        Returns:
            List of test case dictionaries
        """
        prompt = f"""You are a prompt testing expert. Generate {num_cases} diverse, realistic test cases for this prompt template.

Return a JSON array of test case objects. Each object should have:
- "inputs": dict of variable values to test
- "purpose": brief description of what this test case validates

Focus on:
- Edge cases (empty values, very long inputs, special characters)
- Typical use cases
- Boundary conditions

Template to test:

{template}

Test cases (JSON only):"""

        response = await self.llm.execute(
            prompt=prompt,
            model=self.model,
            temperature=0.5,
            max_tokens=2000,
        )

        try:
            # Extract JSON from response
            content = response.content.strip()
            # Remove markdown code blocks if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            test_cases = json.loads(content)
            return test_cases if isinstance(test_cases, list) else []
        except (json.JSONDecodeError, IndexError):
            # Fallback to empty list if parsing fails
            return []

    async def _evaluate_with_llm(
        self,
        original_template: str,
        variant: Variant,
        test_cases: list[dict],
    ) -> dict[str, Any]:
        """
        Use LLM as a critic to evaluate variant quality.

        Args:
            original_template: Original template
            variant: Variant to evaluate
            test_cases: Test cases for evaluation context

        Returns:
            Dictionary with score (float) and insights (list[Insight])
        """
        test_cases_str = json.dumps(test_cases, indent=2)

        prompt = f"""You are an expert prompt engineering critic. Evaluate how well the optimized prompt improves on the original.

Analyze:
1. Does it preserve all variables and includes?
2. Is it clearer and less ambiguous?
3. Does it provide better structure or constraints?
4. Is it more token-efficient?
5. Does it maintain the original intent?

Return a JSON object with:
{{
  "score": <float 0-10>,
  "insights": [
    {{
      "category": "clarity" | "specificity" | "efficiency",
      "description": "What was improved",
      "impact": "Concrete benefit (e.g., '15% fewer tokens', 'reduces parsing errors')"
    }}
  ]
}}

Be specific about improvements. Focus on concrete, observable benefits.

Original template:
{original_template}

Optimized variant ({variant.strategy}):
{variant.template}

Test cases context:
{test_cases_str}

Evaluation (JSON only):"""

        response = await self.llm.execute(
            prompt=prompt,
            model=self.model,
            temperature=0.3,
            max_tokens=2000,
        )

        try:
            # Extract JSON from response
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            evaluation = json.loads(content)

            # Parse insights into Insight objects
            insights = [
                Insight(
                    category=insight.get("category", variant.strategy),
                    description=insight.get("description", ""),
                    impact=insight.get("impact", ""),
                )
                for insight in evaluation.get("insights", [])
            ]

            return {
                "score": float(evaluation.get("score", 5.0)),
                "insights": insights,
            }

        except (json.JSONDecodeError, IndexError, KeyError, ValueError):
            # Fallback if parsing fails
            return {
                "score": 5.0,
                "insights": [],
            }