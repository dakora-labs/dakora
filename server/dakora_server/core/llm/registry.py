"""Provider registry for workspace-scoped LLM provider lookup."""

from typing import cast

from ...config import get_settings
from .azure_openai import AzureOpenAIProvider
from .provider import LLMProvider


class ProviderRegistry:
    """Registry for managing LLM providers per workspace."""

    def __init__(self) -> None:
        """Initialize provider registry."""
        self._settings = get_settings()
        self._cached_provider: AzureOpenAIProvider | None = None

    def get_provider(self, workspace_id: str) -> LLMProvider:
        """Get LLM provider for a workspace.

        Phase 1: Always returns shared AzureOpenAIProvider.
        Future: Check if workspace has BYOK configured and return
        appropriate provider.

        Args:
            workspace_id: Workspace ID to get provider for

        Returns:
            LLMProvider instance

        Raises:
            ValueError: If Azure OpenAI is not configured
        """
        # Phase 1: Always use shared Azure OpenAI provider
        if not self._cached_provider:
            if not self._settings.azure_openai_endpoint:
                raise ValueError("Azure OpenAI endpoint not configured")
            if not self._settings.azure_openai_api_key:
                raise ValueError("Azure OpenAI API key not configured")

            self._cached_provider = AzureOpenAIProvider(
                endpoint=self._settings.azure_openai_endpoint,
                api_key=self._settings.azure_openai_api_key,
                deployment_name=self._settings.azure_openai_deployment_name,
            )

        return cast(LLMProvider, self._cached_provider)


# Global registry instance
_registry = ProviderRegistry()


def get_provider_registry() -> ProviderRegistry:
    """Get global provider registry instance."""
    return _registry