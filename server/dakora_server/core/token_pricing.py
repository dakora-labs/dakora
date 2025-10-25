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

from typing import Optional, Dict, Tuple

# Pricing table: (provider, model) -> (input_cost_per_1k, output_cost_per_1k)
# Costs are in USD per 1,000 tokens
# TODO: Move to database table for dynamic updates
PRICING_TABLE: Dict[Tuple[str, str], Tuple[float, float]] = {
    # OpenAI Models
    ("openai", "gpt-4"): (0.03, 0.06),
    ("openai", "gpt-4-32k"): (0.06, 0.12),
    ("openai", "gpt-4-turbo"): (0.01, 0.03),
    ("openai", "gpt-4-turbo-preview"): (0.01, 0.03),
    ("openai", "gpt-4o"): (0.005, 0.015),
    ("openai", "gpt-4o-mini"): (0.00015, 0.0006),
    ("openai", "gpt-3.5-turbo"): (0.0015, 0.002),
    ("openai", "gpt-3.5-turbo-16k"): (0.003, 0.004),
    
    # Azure OpenAI (same pricing as OpenAI)
    ("azure_openai", "gpt-4"): (0.03, 0.06),
    ("azure_openai", "gpt-4-32k"): (0.06, 0.12),
    ("azure_openai", "gpt-4-turbo"): (0.01, 0.03),
    ("azure_openai", "gpt-4o"): (0.005, 0.015),
    ("azure_openai", "gpt-4o-mini"): (0.00015, 0.0006),
    ("azure_openai", "gpt-35-turbo"): (0.0015, 0.002),
    ("azure_openai", "gpt-35-turbo-16k"): (0.003, 0.004),
    
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
}


class TokenPricingService:
    """Service for calculating LLM execution costs based on token usage."""
    
    def __init__(self, pricing_table: Optional[Dict[Tuple[str, str], Tuple[float, float]]] = None):
        """
        Initialize pricing service.
        
        Args:
            pricing_table: Optional custom pricing table. Defaults to PRICING_TABLE.
        """
        self.pricing_table = pricing_table or PRICING_TABLE
    
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
        
        # Look up pricing
        key = (provider_norm, model_norm)
        if key not in self.pricing_table:
            # Try without version suffix (e.g., gpt-4 from gpt-4-turbo)
            model_parts = model_norm.split("-")
            if len(model_parts) >= 2:
                model_base = "-".join(model_parts[0:2])
                key = (provider_norm, model_base)
                
                if key not in self.pricing_table:
                    return None
            else:
                return None
        
        input_cost_per_1k, output_cost_per_1k = self.pricing_table[key]
        
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
        key = (provider_norm, model_norm)
        return self.pricing_table.get(key)


# Singleton instance for easy access
_pricing_service: Optional[TokenPricingService] = None


def get_pricing_service() -> TokenPricingService:
    """Get the global token pricing service instance."""
    global _pricing_service
    if _pricing_service is None:
        _pricing_service = TokenPricingService()
    return _pricing_service
