"""Tests for Google Gemini provider."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dakora_server.core.llm.google_gemini import GoogleGeminiProvider
from dakora_server.core.llm.provider import ExecutionResult, ModelInfo
from dakora_server.core.token_pricing import get_pricing_service


class TestGoogleGeminiProvider:
    """Tests for GoogleGeminiProvider."""

    @pytest.fixture
    def provider(self):
        """Create provider instance."""
        with patch("dakora_server.core.llm.google_gemini.genai.configure"):
            return GoogleGeminiProvider(api_key="test-gemini-key")

    @pytest.mark.asyncio
    async def test_execute_success(self, provider):
        """Test successful prompt execution."""
        # Mock the Gemini response
        mock_response = MagicMock()
        mock_response.usage_metadata = MagicMock(
            prompt_token_count=50,
            candidates_token_count=100,
            total_token_count=150,
        )
        mock_response.text = "Hello from Gemini!"

        mock_model = MagicMock()
        mock_model.generate_content_async = AsyncMock(return_value=mock_response)

        with patch(
            "dakora_server.core.llm.google_gemini.genai.GenerativeModel",
            return_value=mock_model,
        ):
            result = await provider.execute("Test prompt", model="gemini-2.5-flash")

            assert isinstance(result, ExecutionResult)
            assert result.content == "Hello from Gemini!"
            assert result.tokens_input == 50
            assert result.tokens_output == 100
            assert result.tokens_total == 150
            assert result.model == "gemini-2.5-flash"
            assert result.provider == "google_gemini"
            assert result.cost_usd > 0
            assert result.latency_ms >= 0

    @pytest.mark.asyncio
    async def test_execute_requires_model(self, provider):
        """Test that model parameter is required."""
        with pytest.raises(ValueError, match="model parameter is required"):
            await provider.execute("Test prompt")

    @pytest.mark.asyncio
    async def test_execute_with_generation_config(self, provider):
        """Test execution with temperature and max_tokens."""
        mock_response = MagicMock()
        mock_response.usage_metadata = MagicMock(
            prompt_token_count=10,
            candidates_token_count=20,
            total_token_count=30,
        )
        mock_response.text = "Response"

        mock_model = MagicMock()
        mock_model.generate_content_async = AsyncMock(return_value=mock_response)

        with patch(
            "dakora_server.core.llm.google_gemini.genai.GenerativeModel",
            return_value=mock_model,
        ):
            await provider.execute(
                "Test prompt",
                model="gemini-2.5-pro",
                temperature=0.7,
                max_tokens=1024,
            )

            # Verify generation_config was passed
            call_args = mock_model.generate_content_async.call_args
            assert call_args[1]["generation_config"] is not None
            assert call_args[1]["generation_config"]["temperature"] == 0.7
            assert call_args[1]["generation_config"]["max_output_tokens"] == 1024

    @pytest.mark.asyncio
    async def test_execute_error_handling(self, provider):
        """Test error handling during execution."""
        mock_model = MagicMock()
        mock_model.generate_content_async = AsyncMock(
            side_effect=Exception("API Error")
        )

        with patch(
            "dakora_server.core.llm.google_gemini.genai.GenerativeModel",
            return_value=mock_model,
        ):
            with pytest.raises(Exception, match="Google Gemini execution failed"):
                await provider.execute("Test prompt", model="gemini-2.5-flash")

    @pytest.mark.asyncio
    async def test_execute_missing_usage(self, provider):
        """Test error handling when usage information is missing."""
        mock_response = MagicMock()
        mock_response.usage_metadata = None

        mock_model = MagicMock()
        mock_model.generate_content_async = AsyncMock(return_value=mock_response)

        with patch(
            "dakora_server.core.llm.google_gemini.genai.GenerativeModel",
            return_value=mock_model,
        ):
            with pytest.raises(Exception, match="Google Gemini execution failed"):
                await provider.execute("Test prompt", model="gemini-2.5-flash")

    def test_get_available_models(self, provider):
        """Test retrieving available models."""
        models = provider.get_available_models()

        assert len(models) == 2
        assert all(isinstance(m, ModelInfo) for m in models)

        # Check both models are present
        model_ids = {m.id for m in models}
        assert "gemini-2.5-pro" in model_ids
        assert "gemini-2.5-flash" in model_ids

        # Check Gemini 2.5 Flash details
        flash = next((m for m in models if m.id == "gemini-2.5-flash"), None)
        assert flash is not None
        assert flash.name == "Gemini 2.5 Flash"
        assert flash.provider == "google_gemini"
        assert flash.input_cost_per_1k == 0.0003
        assert flash.output_cost_per_1k == 0.0025
        assert flash.max_tokens == 1048576

        # Check Gemini 2.5 Pro details
        pro = next((m for m in models if m.id == "gemini-2.5-pro"), None)
        assert pro is not None
        assert pro.name == "Gemini 2.5 Pro"
        assert pro.provider == "google_gemini"
        assert pro.input_cost_per_1k == 0.00125
        assert pro.output_cost_per_1k == 0.01
        assert pro.max_tokens == 1048576

    def test_cost_calculation_flash(self, provider):
        """Test cost calculation for Gemini 2.5 Flash (flat pricing)."""
        # Gemini 2.5 Flash pricing
        input_tokens = 1000
        output_tokens = 1000
        svc = get_pricing_service()
        pricing = svc.get_pricing("google", "gemini-2.5-flash")
        assert pricing is not None, "pricing for gemini-2.5-flash must exist in TokenPricingService"
        input_cost_per_1k, output_cost_per_1k = pricing

        expected_cost = (
            input_tokens / 1000 * input_cost_per_1k
            + output_tokens / 1000 * output_cost_per_1k
        )

        # Cost should be: 0.0003 + 0.0025 = 0.0028
        assert expected_cost == 0.0028

    def test_cost_calculation_pro_low_tier(self, provider):
        """Test cost calculation for Gemini 2.5 Pro (low tier <= 200k tokens)."""
        # Gemini 2.5 Pro pricing (low tier)
        input_tokens = 100000  # 100k tokens (below 200k threshold)
        output_tokens = 10000
        svc = get_pricing_service()
        pricing = svc.get_pricing("google", "gemini-2.5-pro")
        assert pricing is not None, "pricing for gemini-2.5-pro must exist in TokenPricingService"
        # TokenPricingService may store tiered pricing; get_pricing returns the representative (low-tier) tuple
        input_cost_per_1k, output_cost_per_1k = pricing

        expected_cost = (
            input_tokens / 1000 * input_cost_per_1k
            + output_tokens / 1000 * output_cost_per_1k
        )

        # Cost should be: 100 * 0.00125 + 10 * 0.01 = 0.125 + 0.1 = 0.225
        assert expected_cost == 0.225

    def test_cost_calculation_pro_high_tier(self, provider):
        """Test cost calculation for Gemini 2.5 Pro (high tier > 200k tokens)."""
        # Gemini 2.5 Pro pricing (high tier)
        input_tokens = 250000  # 250k tokens (above 200k threshold)
        output_tokens = 10000
        svc = get_pricing_service()
        # For high-tier calculation we can call calculate_cost directly which applies tier thresholds
        expected_cost = svc.calculate_cost(
            provider="google",
            model="gemini-2.5-pro",
            tokens_in=input_tokens,
            tokens_out=output_tokens,
        )

        # Cost should be: 250 * 0.0025 + 10 * 0.015 = 0.625 + 0.15 = 0.775
        assert expected_cost == 0.775