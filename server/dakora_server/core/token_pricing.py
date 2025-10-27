"""Token pricing service for LLM execution cost calculation.

This module provides centralized pricing logic for calculating the cost of LLM
executions based on token usage. Costs are calculated server-side to ensure
consistent pricing across all clients and easy updates.

TODO: Replace hardcoded pricing with dynamic pricing from database/external API.
This would allow:
- Real-time pricing updates without code changes
- Regional pricing variations
- Volume discounts and enterprise pricing
- Historical cost tracking (cost at execution time vs current cost)
"""

from typing import Optional, Dict, Tuple, Union, Any

# Pricing table: (provider, model) -> pricing entry
# Pricing entries may be one of:
# - (input_per_1k, output_per_1k)  -- flat pricing tuple
# - dict with keys for tiered pricing and thresholds, e.g. {
#     'type': 'tiered', 'input_low': ..., 'input_high': ..., 'output_low': ..., 'output_high': ..., 'tier_threshold': ...
#   }
# This allows centralizing more complex pricing rules in one place.
PRICING_TABLE: Dict[Tuple[str, str], Union[Tuple[float, float], Dict[str, Any]]] = {
    # OpenAI Models
    ("openai", "gpt-4"): (0.03, 0.06),
    ("openai", "gpt-4-32k"): (0.06, 0.12),
    ("openai", "gpt-4-turbo"): (0.01, 0.03),
    ("openai", "gpt-4-turbo-preview"): (0.01, 0.03),
    ("openai", "gpt-4o"): (0.005, 0.015),
    ("openai", "gpt-4o-mini"): (0.00015, 0.0006),
    ("openai", "gpt-3.5-turbo"): (0.0015, 0.002),
    ("openai", "gpt-3.5-turbo-16k"): (0.003, 0.004),
    ("openai", "gpt-5"): (0.05, 0.12),
    ("openai", "gpt-5-mini"): (0.0025, 0.006),
    
    # Azure OpenAI (same pricing as OpenAI)
    ("azure_openai", "gpt-4"): (0.03, 0.06),
    ("azure_openai", "gpt-4-32k"): (0.06, 0.12),
    ("azure_openai", "gpt-4-turbo"): (0.01, 0.03),
    ("azure_openai", "gpt-4o"): (0.005, 0.015),
    ("azure_openai", "gpt-4o-mini"): (0.00015, 0.0006),
    ("azure_openai", "gpt-35-turbo"): (0.0015, 0.002),
    ("azure_openai", "gpt-35-turbo-16k"): (0.003, 0.004),
    ("azure_openai", "gpt-5"): (0.05, 0.12),
    ("azure_openai", "gpt-5-mini"): (0.0025, 0.006),
    
    # Anthropic Models
    ("anthropic", "claude-3-opus-20240229"): (0.015, 0.075),
    ("anthropic", "claude-3-sonnet-20240229"): (0.003, 0.015),
    ("anthropic", "claude-3-haiku-20240307"): (0.00025, 0.00125),
    ("anthropic", "claude-3-5-sonnet-20241022"): (0.003, 0.015),
    ("anthropic", "claude-2.1"): (0.008, 0.024),
    ("anthropic", "claude-2.0"): (0.008, 0.024),
    ("anthropic", "claude-instant-1.2"): (0.0008, 0.0024),
    
    # Google Models (Gemini)
    ("google", "gemini-pro"): (0.00025, 0.00075),
    ("google", "gemini-pro-vision"): (0.00025, 0.00075),
    ("google", "gemini-ultra"): (0.00125, 0.00375),
    ("google", "gemini-1.5-pro"): (0.00125, 0.00375),
    ("google", "gemini-1.5-flash"): (0.000075, 0.0003),
    # Tiered pricing example for modern Gemini models
    ("google", "gemini-2.5-pro"): {
        "type": "tiered",
        "input_low": 0.00125,
        "input_high": 0.0025,
        "output_low": 0.01,
        "output_high": 0.015,
        "tier_threshold": 200000,
    },
    ("google", "gemini-2.5-flash"): {"type": "flat", "input": 0.0003, "output": 0.0025},
}


class TokenPricingService:
    """Service for calculating LLM execution costs based on token usage."""
    
    def __init__(
        self,
        pricing_table: Optional[Dict[Tuple[str, str], Union[Tuple[float, float], Dict[str, Any]]]] = None,
    ):
        """
        Initialize pricing service.
        
        Args:
            pricing_table: Optional custom pricing table. Defaults to PRICING_TABLE.
        """
        # pricing_table can contain either flat tuples or dict entries (tiered/flat)
        # Annotate attribute so static checkers know the value shape.
        self.pricing_table: Dict[Tuple[str, str], Union[Tuple[float, float], Dict[str, Any]]] = (
            pricing_table or PRICING_TABLE
        )
    
    def calculate_cost(
        self,
        provider: Optional[str],
        model: Optional[str],
        tokens_in: Optional[int],
        tokens_out: Optional[int],
    ) -> Optional[float]:
        """
        Calculate cost in USD for a given execution.
        
        Args:
            provider: Provider name (e.g., "openai", "anthropic")
            model: Model identifier (e.g., "gpt-4", "claude-3-opus")
            tokens_in: Input token count
            tokens_out: Output token count
            
        Returns:
            Cost in USD, or None if pricing not available or inputs invalid
        """
        # Validate all required inputs are present
        if not provider or not model or tokens_in is None or tokens_out is None:
            return None
        
        # Normalize provider and model names
        provider_norm = self._normalize_provider(provider)
        model_norm = self._normalize_model(model)
        
        # Look up pricing entry
        key = (provider_norm, model_norm)
        entry = self.pricing_table.get(key)

        # Try simpler base model match if not found, e.g., gpt-4 from gpt-4-turbo
        if entry is None:
            model_parts = model_norm.split("-")
            if len(model_parts) >= 2:
                model_base = "-".join(model_parts[0:2])
                key = (provider_norm, model_base)
                entry = self.pricing_table.get(key)

        if entry is None:
            return None

        # Entry can be a flat tuple or a dict describing type
        if isinstance(entry, tuple):
            input_cost_per_1k, output_cost_per_1k = entry
        else:
            etype = entry.get("type")
            if etype == "tiered":
                threshold = entry.get("tier_threshold", float("inf"))
                # tokens_in is guaranteed non-None by earlier validation
                if tokens_in > threshold:
                    input_cost_per_1k = entry.get("input_high")
                    output_cost_per_1k = entry.get("output_high")
                else:
                    input_cost_per_1k = entry.get("input_low")
                    output_cost_per_1k = entry.get("output_low")
            elif etype == "flat":
                input_cost_per_1k = entry.get("input")
                output_cost_per_1k = entry.get("output")
            else:
                # Unknown dict shape
                return None

        # Validate numeric pricing values
        if input_cost_per_1k is None or output_cost_per_1k is None:
            return None

        # Calculate cost
        input_cost = (tokens_in / 1000) * input_cost_per_1k
        output_cost = (tokens_out / 1000) * output_cost_per_1k
        total_cost = input_cost + output_cost

        return round(total_cost, 8)  # Round to 8 decimal places
    
    def _normalize_provider(self, provider: str) -> str:
        """Normalize provider name to match pricing table keys."""
        provider_lower = provider.lower()
        
        if "azure" in provider_lower:
            return "azure_openai"
        elif "openai" in provider_lower:
            return "openai"
        elif "anthropic" in provider_lower or "claude" in provider_lower:
            return "anthropic"
        elif "google" in provider_lower or "gemini" in provider_lower:
            return "google"
        
        return provider_lower
    
    def _normalize_model(self, model: str) -> str:
        """Normalize model name to match pricing table keys."""
        return model.lower().strip()
    
    def get_pricing(self, provider: str, model: str) -> Optional[Tuple[float, float]]:
        """
        Get pricing for a specific provider and model.
        
        Args:
            provider: Provider name
            model: Model identifier
            
        Returns:
            Tuple of (input_cost_per_1k, output_cost_per_1k) or None if not found
        """
        provider_norm = self._normalize_provider(provider)
        model_norm = self._normalize_model(model)

        entry = self.pricing_table.get((provider_norm, model_norm))
        if entry is None:
            # Try base model
            parts = model_norm.split("-")
            if len(parts) >= 2:
                base = "-".join(parts[0:2])
                entry = self.pricing_table.get((provider_norm, base))

        if entry is None:
            return None

        if isinstance(entry, tuple):
            # Ensure both elements are floats
            try:
                return (float(entry[0]), float(entry[1]))
            except Exception:
                return None
        else:
            etype = entry.get("type")
            if etype == "tiered":
                in_low = entry.get("input_low")
                out_low = entry.get("output_low")
                if in_low is None or out_low is None:
                    return None
                try:
                    return (float(in_low), float(out_low))
                except Exception:
                    return None
            elif etype == "flat":
                in_flat = entry.get("input")
                out_flat = entry.get("output")
                if in_flat is None or out_flat is None:
                    return None
                try:
                    return (float(in_flat), float(out_flat))
                except Exception:
                    return None

        return None


# Singleton instance for easy access
_pricing_service: Optional[TokenPricingService] = None


def get_pricing_service() -> TokenPricingService:
    """Get the global token pricing service instance."""
    global _pricing_service
    if _pricing_service is None:
        _pricing_service = TokenPricingService()
    return _pricing_service
