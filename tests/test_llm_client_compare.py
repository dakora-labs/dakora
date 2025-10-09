import pytest
from unittest.mock import Mock, patch, AsyncMock
import asyncio

from dakora.llm.client import LLMClient
from dakora.llm.models import ExecutionResult, ComparisonResult


@pytest.fixture
def mock_litellm_responses():
    responses = []

    for i, (provider, model) in enumerate([
        ("openai", "gpt-4"),
        ("anthropic", "claude-3-opus"),
        ("google", "gemini-pro")
    ]):
        response = Mock()
        response.choices = [Mock(message=Mock(content=f"{model} response"))]
        response._hidden_params = {
            "custom_llm_provider": provider,
            "response_cost": 0.01 * (i + 1)
        }
        response.usage = Mock(prompt_tokens=100 + i * 5, completion_tokens=50 + i * 2)
        responses.append(response)

    return responses


class TestLLMClientCompare:
    def test_compare_basic_success(self, mock_litellm_responses):
        client = LLMClient()

        with patch('dakora.llm.client.acompletion') as mock_acompletion:
            mock_acompletion.side_effect = mock_litellm_responses

            result = asyncio.run(client.compare(
                prompt="Test prompt",
                models=["gpt-4", "claude-3-opus", "gemini-pro"]
            ))

            assert isinstance(result, ComparisonResult)
            assert len(result.results) == 3
            assert result.successful_count == 3
            assert result.failed_count == 0

            assert result.results[0].model == "gpt-4"
            assert result.results[0].provider == "openai"
            assert result.results[0].output == "gpt-4 response"

            assert result.results[1].model == "claude-3-opus"
            assert result.results[1].provider == "anthropic"
            assert result.results[1].output == "claude-3-opus response"

            assert result.results[2].model == "gemini-pro"
            assert result.results[2].provider == "google"
            assert result.results[2].output == "gemini-pro response"

    def test_compare_calculates_totals(self, mock_litellm_responses):
        client = LLMClient()

        with patch('dakora.llm.client.acompletion') as mock_acompletion:
            mock_acompletion.side_effect = mock_litellm_responses

            result = asyncio.run(client.compare(
                prompt="Test prompt",
                models=["gpt-4", "claude-3-opus", "gemini-pro"]
            ))

            assert result.total_cost_usd == pytest.approx(0.06, abs=0.001)
            assert result.total_tokens_in == 100 + 105 + 110
            assert result.total_tokens_out == 50 + 52 + 54

    def test_compare_partial_failure(self):
        client = LLMClient()

        async def mock_acompletion_mixed(**kwargs):
            if kwargs["model"] == "gpt-4":
                response = Mock()
                response.choices = [Mock(message=Mock(content="gpt-4 response"))]
                response._hidden_params = {"custom_llm_provider": "openai", "response_cost": 0.01}
                response.usage = Mock(prompt_tokens=100, completion_tokens=50)
                return response
            elif kwargs["model"] == "claude-3-opus":
                raise Exception("Rate limit exceeded for claude-3-opus")
            else:
                response = Mock()
                response.choices = [Mock(message=Mock(content="gemini response"))]
                response._hidden_params = {"custom_llm_provider": "google", "response_cost": 0.02}
                response.usage = Mock(prompt_tokens=105, completion_tokens=52)
                return response

        with patch('dakora.llm.client.acompletion', side_effect=mock_acompletion_mixed):
            result = asyncio.run(client.compare(
                prompt="Test prompt",
                models=["gpt-4", "claude-3-opus", "gemini-pro"]
            ))

            assert result.successful_count == 2
            assert result.failed_count == 1

            assert result.results[0].error is None
            assert result.results[1].error is not None
            assert "Rate limit exceeded" in result.results[1].error
            assert result.results[2].error is None

            assert result.total_cost_usd == pytest.approx(0.03, abs=0.001)
            assert result.total_tokens_in == 205
            assert result.total_tokens_out == 102

    def test_compare_all_failures(self):
        client = LLMClient()

        async def mock_acompletion_fail(**kwargs):
            raise Exception("Rate limit exceeded")

        with patch('dakora.llm.client.acompletion', side_effect=mock_acompletion_fail):
            result = asyncio.run(client.compare(
                prompt="Test prompt",
                models=["gpt-4", "claude-3-opus"]
            ))

            assert result.successful_count == 0
            assert result.failed_count == 2
            assert all(r.error is not None for r in result.results)
            assert all("Rate limit exceeded" in r.error for r in result.results)

            assert result.total_cost_usd == 0.0
            assert result.total_tokens_in == 0
            assert result.total_tokens_out == 0

    def test_compare_preserves_model_order(self):
        client = LLMClient()

        models = ["gemini-pro", "gpt-4", "claude-3-opus"]

        async def mock_acompletion_ordered(**kwargs):
            model = kwargs["model"]
            response = Mock()
            response.choices = [Mock(message=Mock(content=f"{model} response"))]
            response._hidden_params = {"custom_llm_provider": "provider", "response_cost": 0.01}
            response.usage = Mock(prompt_tokens=100, completion_tokens=50)
            return response

        with patch('dakora.llm.client.acompletion', side_effect=mock_acompletion_ordered):
            result = asyncio.run(client.compare(prompt="Test prompt", models=models))

            assert [r.model for r in result.results] == models

    def test_compare_with_llm_params(self, mock_litellm_responses):
        client = LLMClient()

        with patch('dakora.llm.client.acompletion') as mock_acompletion:
            mock_acompletion.side_effect = mock_litellm_responses

            result = asyncio.run(client.compare(
                prompt="Test prompt",
                models=["gpt-4", "claude-3-opus"],
                temperature=0.7,
                max_tokens=100
            ))

            assert result.successful_count == 2

            for call in mock_acompletion.call_args_list:
                assert call[1]["temperature"] == 0.7
                assert call[1]["max_tokens"] == 100

    def test_compare_single_model(self):
        client = LLMClient()

        async def mock_acompletion_single(**kwargs):
            response = Mock()
            response.choices = [Mock(message=Mock(content="response"))]
            response._hidden_params = {"custom_llm_provider": "openai", "response_cost": 0.01}
            response.usage = Mock(prompt_tokens=100, completion_tokens=50)
            return response

        with patch('dakora.llm.client.acompletion', side_effect=mock_acompletion_single):
            result = asyncio.run(client.compare(prompt="Test prompt", models=["gpt-4"]))

            assert len(result.results) == 1
            assert result.successful_count == 1
            assert result.failed_count == 0

    def test_compare_timeout_error(self):
        client = LLMClient()

        async def mock_acompletion_timeout(**kwargs):
            if kwargs["model"] == "gpt-4":
                raise Exception("Request timeout")
            response = Mock()
            response.choices = [Mock(message=Mock(content="response"))]
            response._hidden_params = {"custom_llm_provider": "anthropic", "response_cost": 0.01}
            response.usage = Mock(prompt_tokens=100, completion_tokens=50)
            return response

        with patch('dakora.llm.client.acompletion', side_effect=mock_acompletion_timeout):
            result = asyncio.run(client.compare(
                prompt="Test prompt",
                models=["gpt-4", "claude-3-opus"]
            ))

            assert result.successful_count == 1
            assert result.failed_count == 1
            assert "timeout" in result.results[0].error.lower()

    def test_compare_bad_request_error(self):
        client = LLMClient()

        async def mock_acompletion_bad_request(**kwargs):
            if kwargs["model"] == "invalid-model":
                raise Exception("Invalid model")
            response = Mock()
            response.choices = [Mock(message=Mock(content="response"))]
            response._hidden_params = {"custom_llm_provider": "openai", "response_cost": 0.01}
            response.usage = Mock(prompt_tokens=100, completion_tokens=50)
            return response

        with patch('dakora.llm.client.acompletion', side_effect=mock_acompletion_bad_request):
            result = asyncio.run(client.compare(
                prompt="Test prompt",
                models=["gpt-4", "invalid-model"]
            ))

            assert result.successful_count == 1
            assert result.failed_count == 1
            assert "Invalid model" in result.results[1].error

    def test_compare_handles_missing_usage(self):
        client = LLMClient()

        async def mock_acompletion_no_usage(**kwargs):
            response = Mock()
            response.choices = [Mock(message=Mock(content="response"))]
            response._hidden_params = {"custom_llm_provider": "openai", "response_cost": 0.01}
            response.usage = None
            return response

        with patch('dakora.llm.client.acompletion', side_effect=mock_acompletion_no_usage):
            result = asyncio.run(client.compare(prompt="Test prompt", models=["gpt-4"]))

            assert result.results[0].tokens_in == 0
            assert result.results[0].tokens_out == 0
            assert result.total_tokens_in == 0
            assert result.total_tokens_out == 0

    def test_compare_handles_missing_cost(self):
        client = LLMClient()

        async def mock_acompletion_no_cost(**kwargs):
            response = Mock()
            response.choices = [Mock(message=Mock(content="response"))]
            response._hidden_params = {"custom_llm_provider": "openai"}
            response.usage = Mock(prompt_tokens=100, completion_tokens=50)
            return response

        with patch('dakora.llm.client.acompletion', side_effect=mock_acompletion_no_cost):
            result = asyncio.run(client.compare(prompt="Test prompt", models=["gpt-4"]))

            assert result.results[0].cost_usd == 0.0
            assert result.total_cost_usd == 0.0

    def test_compare_handles_empty_output(self):
        client = LLMClient()

        async def mock_acompletion_empty(**kwargs):
            response = Mock()
            response.choices = [Mock(message=Mock(content=None, refusal=None))]
            response._hidden_params = {"custom_llm_provider": "openai", "response_cost": 0.01}
            response.usage = Mock(prompt_tokens=100, completion_tokens=0)
            return response

        with patch('dakora.llm.client.acompletion', side_effect=mock_acompletion_empty):
            result = asyncio.run(client.compare(prompt="Test prompt", models=["gpt-4"]))

            assert result.results[0].output == ""
            assert result.successful_count == 1
