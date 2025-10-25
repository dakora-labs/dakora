"""Tests for LLM provider module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dakora_server.core.llm import (
    AzureOpenAIProvider,
    ExecutionResult,
    ModelInfo,
    ProviderRegistry,
)


class TestAzureOpenAIProvider:
    """Tests for AzureOpenAIProvider."""

    @pytest.fixture
    def provider(self):
        """Create provider instance."""
        return AzureOpenAIProvider(
            endpoint="https://test.openai.azure.com/",
            api_key="test-key",
            deployment_name="gpt-4o",
        )

    @pytest.mark.asyncio
    async def test_execute_success(self, provider):
        """Test successful prompt execution."""
        # Mock the OpenAI response
        mock_response = MagicMock()
        mock_response.usage = MagicMock(
            prompt_tokens=45, completion_tokens=120, total_tokens=165
        )
        mock_response.choices = [
            MagicMock(message=MagicMock(content="Hello Alice!"))
        ]

        with patch.object(
            provider.client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            result = await provider.execute("Say hello", model="gpt-4o")

            assert isinstance(result, ExecutionResult)
            assert result.content == "Hello Alice!"
            assert result.tokens_input == 45
            assert result.tokens_output == 120
            assert result.tokens_total == 165
            assert result.model == "gpt-4o"
            assert result.provider == "azure_openai"
            assert result.cost_usd > 0
            assert result.latency_ms >= 0

    @pytest.mark.asyncio
    async def test_execute_with_default_model(self, provider):
        """Test execution uses default deployment when model not specified."""
        mock_response = MagicMock()
        mock_response.usage = MagicMock(
            prompt_tokens=10, completion_tokens=20, total_tokens=30
        )
        mock_response.choices = [MagicMock(message=MagicMock(content="Response"))]

        with patch.object(
            provider.client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            result = await provider.execute("Test prompt")

            assert result.model == "gpt-4o"
            mock_create.assert_called_once()
            call_args = mock_create.call_args
            assert call_args[1]["model"] == "gpt-4o"

    @pytest.mark.asyncio
    async def test_execute_error_handling(self, provider):
        """Test error handling during execution."""
        with patch.object(
            provider.client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.side_effect = Exception("API Error")

            with pytest.raises(Exception, match="Azure OpenAI execution failed"):
                await provider.execute("Test prompt")

    @pytest.mark.asyncio
    async def test_execute_missing_usage(self, provider):
        """Test error handling when usage information is missing."""
        mock_response = MagicMock()
        mock_response.usage = None

        with patch.object(
            provider.client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            with pytest.raises(Exception, match="Azure OpenAI execution failed"):
                await provider.execute("Test prompt")

    def test_get_available_models(self, provider):
        """Test retrieving available models."""
        models = provider.get_available_models()

        assert len(models) > 0
        assert all(isinstance(m, ModelInfo) for m in models)

        # Check GPT-4o is in the list
        gpt4o = next((m for m in models if m.id == "gpt-4o"), None)
        assert gpt4o is not None
        assert gpt4o.name == "GPT-4o"
        assert gpt4o.provider == "azure_openai"
        assert gpt4o.input_cost_per_1k > 0
        assert gpt4o.output_cost_per_1k > 0
        assert gpt4o.max_tokens > 0

    def test_cost_calculation(self, provider):
        """Test cost calculation for different models."""
        # GPT-4o pricing
        input_tokens = 1000
        output_tokens = 1000
        pricing = provider.PRICING["gpt-4o"]

        expected_cost = (
            input_tokens / 1000 * pricing["input"]
            + output_tokens / 1000 * pricing["output"]
        )

        # Cost should be calculated correctly
        assert expected_cost == 0.0025 + 0.01


class TestProviderRegistry:
    """Tests for ProviderRegistry."""

    def test_get_provider_returns_azure_openai(self):
        """Test registry returns AzureOpenAIProvider for any workspace."""
        with patch("dakora_server.core.llm.registry.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                azure_openai_endpoint="https://test.openai.azure.com/",
                azure_openai_api_key="test-key",
                azure_openai_deployment_name="gpt-4o",
            )

            registry = ProviderRegistry()
            provider = registry.get_provider("workspace-123")

            assert isinstance(provider, AzureOpenAIProvider)

    def test_get_provider_caching(self):
        """Test provider is cached after first call."""
        with patch("dakora_server.core.llm.registry.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                azure_openai_endpoint="https://test.openai.azure.com/",
                azure_openai_api_key="test-key",
                azure_openai_deployment_name="gpt-4o",
            )

            registry = ProviderRegistry()
            provider1 = registry.get_provider("workspace-123")
            provider2 = registry.get_provider("workspace-456")

            # Should return same instance
            assert provider1 is provider2

    def test_get_provider_missing_config(self):
        """Test error when Azure OpenAI is not configured."""
        with patch("dakora_server.core.llm.registry.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                azure_openai_endpoint="",
                azure_openai_api_key="",
                azure_openai_deployment_name="gpt-4o",
            )

            registry = ProviderRegistry()

            with pytest.raises(ValueError, match="endpoint not configured"):
                registry.get_provider("workspace-123")