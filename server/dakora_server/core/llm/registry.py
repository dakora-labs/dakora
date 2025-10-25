"""Provider registry for workspace-scoped LLM provider lookup."""

from typing import cast

from ...config import get_settings
from .azure_openai import AzureOpenAIProvider
from .google_gemini import GoogleGeminiProvider
from .provider import LLMProvider, ModelInfo


class ProviderRegistry:
    """Registry for managing LLM providers per workspace."""

    def __init__(self) -> None:
        """Initialize provider registry."""
        self._settings = get_settings()
        self._cached_providers: dict[str, LLMProvider] = {}

    def _initialize_providers(self) -> None:
        """Initialize all configured providers (lazy initialization)."""
        if self._cached_providers:
            return  # Already initialized

        # Initialize Azure OpenAI if configured
        if self._settings.azure_openai_endpoint and self._settings.azure_openai_api_key:
            self._cached_providers["azure_openai"] = AzureOpenAIProvider(
                endpoint=self._settings.azure_openai_endpoint,
                api_key=self._settings.azure_openai_api_key,
                deployment_name=self._settings.azure_openai_deployment_name,
            )

        # Initialize Google Gemini if configured
        if self._settings.google_gemini_api_key:
            self._cached_providers["google_gemini"] = GoogleGeminiProvider(
                api_key=self._settings.google_gemini_api_key,
            )

    def get_provider(self, workspace_id: str) -> LLMProvider:
        """Get LLM provider for a workspace.

        Deprecated: Use get_provider_by_name() instead.
        Returns first available provider for backward compatibility.

        Args:
            workspace_id: Workspace ID to get provider for

        Returns:
            LLMProvider instance

        Raises:
            ValueError: If no providers are configured
        """
        self._initialize_providers()

        if not self._cached_providers:
            raise ValueError("No LLM providers configured")

        # Return first available provider for backward compatibility
        return cast(LLMProvider, next(iter(self._cached_providers.values())))

    def get_all_providers(self, workspace_id: str) -> dict[str, LLMProvider]:
        """Get all configured LLM providers for a workspace.

        Future: Check if workspace has BYOK configured and return
        workspace-specific providers.

        Args:
            workspace_id: Workspace ID to get providers for

        Returns:
            Dictionary mapping provider name to LLMProvider instance
        """
        self._initialize_providers()
        return self._cached_providers.copy()

    def get_provider_by_name(self, workspace_id: str, provider_name: str) -> LLMProvider:
        """Get specific LLM provider by name.

        Args:
            workspace_id: Workspace ID to get provider for
            provider_name: Provider name (e.g., "azure_openai", "google_gemini")

        Returns:
            LLMProvider instance

        Raises:
            ValueError: If provider is not configured
        """
        self._initialize_providers()

        if provider_name not in self._cached_providers:
            raise ValueError(
                f"Provider '{provider_name}' is not configured. "
                f"Available providers: {list(self._cached_providers.keys())}"
            )

        return cast(LLMProvider, self._cached_providers[provider_name])

    def get_all_models(self, workspace_id: str) -> list[ModelInfo]:
        """Get all available models across all configured providers.

        Args:
            workspace_id: Workspace ID to get models for

        Returns:
            List of ModelInfo objects from all providers
        """
        self._initialize_providers()

        all_models: list[ModelInfo] = []
        for provider in self._cached_providers.values():
            all_models.extend(provider.get_available_models())

        return all_models


# Global registry instance
_registry = ProviderRegistry()


def get_provider_registry() -> ProviderRegistry:
    """Get global provider registry instance."""
    return _registry