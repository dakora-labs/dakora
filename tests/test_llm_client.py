import pytest
from unittest.mock import Mock, patch
from litellm.exceptions import (
    AuthenticationError,
    RateLimitError as LiteLLMRateLimitError,
    BadRequestError,
    Timeout,
    APIError
)

from dakora.llm.client import LLMClient
from dakora.exceptions import APIKeyError, RateLimitError, ModelNotFoundError, LLMError

@pytest.fixture
def llm_client():
    return LLMClient()

@pytest.fixture
def mock_litellm_response():
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "This is a test response from the LLM."
    mock_response.usage = Mock()
    mock_response.usage.prompt_tokens = 150
    mock_response.usage.completion_tokens = 80
    mock_response._hidden_params = {
        "custom_llm_provider": "openai",
        "response_cost": 0.03
    }
    return mock_response

def test_execute_success(llm_client, mock_litellm_response):
    with patch("dakora.llm.client.completion", return_value=mock_litellm_response):
        result = llm_client.execute("Test prompt", "gpt-5")

        assert result.output == "This is a test response from the LLM."
        assert result.provider == "openai"
        assert result.model == "gpt-5"
        assert result.tokens_in == 150
        assert result.tokens_out == 80
        assert result.cost_usd == 0.03
        assert result.latency_ms >= 0

def test_execute_anthropic(llm_client):
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "Claude response"
    mock_response.usage = Mock()
    mock_response.usage.prompt_tokens = 200
    mock_response.usage.completion_tokens = 100
    mock_response._hidden_params = {
        "custom_llm_provider": "anthropic",
        "response_cost": 0.05
    }

    with patch("dakora.llm.client.completion", return_value=mock_response):
        result = llm_client.execute("Test prompt", "claude-3-opus")

        assert result.provider == "anthropic"
        assert result.model == "claude-3-opus"
        assert result.output == "Claude response"

def test_execute_missing_usage(llm_client):
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "Response without usage"
    mock_response.usage = None
    mock_response._hidden_params = {"custom_llm_provider": "openai"}

    with patch("dakora.llm.client.completion", return_value=mock_response):
        result = llm_client.execute("Test prompt", "gpt-5")

        assert result.tokens_in == 0
        assert result.tokens_out == 0

def test_execute_missing_cost(llm_client):
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "Response without cost"
    mock_response.usage = Mock()
    mock_response.usage.prompt_tokens = 100
    mock_response.usage.completion_tokens = 50
    mock_response._hidden_params = {"custom_llm_provider": "openai"}

    with patch("dakora.llm.client.completion", return_value=mock_response):
        result = llm_client.execute("Test prompt", "gpt-5")

        assert result.cost_usd == 0.0

def test_execute_empty_output(llm_client):
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = None
    mock_response.usage = Mock()
    mock_response.usage.prompt_tokens = 10
    mock_response.usage.completion_tokens = 0
    mock_response._hidden_params = {"custom_llm_provider": "openai"}

    with patch("dakora.llm.client.completion", return_value=mock_response):
        result = llm_client.execute("Test prompt", "gpt-5")

        assert result.output == ""

def test_execute_authentication_error(llm_client):
    with patch("dakora.llm.client.completion", side_effect=AuthenticationError("Invalid API key", llm_provider="openai", model="gpt-5")):
        with pytest.raises(APIKeyError) as exc_info:
            llm_client.execute("Test prompt", "gpt-5")
        assert "Invalid or missing API key" in str(exc_info.value)
        assert "gpt-5" in str(exc_info.value)

def test_execute_rate_limit_error(llm_client):
    with patch("dakora.llm.client.completion", side_effect=LiteLLMRateLimitError("Rate limit exceeded", llm_provider="openai", model="gpt-5")):
        with pytest.raises(RateLimitError) as exc_info:
            llm_client.execute("Test prompt", "gpt-5")
        assert "Rate limit exceeded" in str(exc_info.value)
        assert "gpt-5" in str(exc_info.value)

def test_execute_model_not_found_error(llm_client):
    with patch("dakora.llm.client.completion", side_effect=BadRequestError("model not found", llm_provider="openai", model="invalid-model")):
        with pytest.raises(ModelNotFoundError) as exc_info:
            llm_client.execute("Test prompt", "invalid-model")
        assert "Model 'invalid-model' not found" in str(exc_info.value)

def test_execute_bad_request_non_model_error(llm_client):
    with patch("dakora.llm.client.completion", side_effect=BadRequestError("Invalid parameter", llm_provider="openai", model="gpt-5")):
        with pytest.raises(LLMError) as exc_info:
            llm_client.execute("Test prompt", "gpt-5")
        assert "Bad request" in str(exc_info.value)

def test_execute_timeout_error(llm_client):
    with patch("dakora.llm.client.completion", side_effect=Timeout(message="Request timed out", model="gpt-5", llm_provider="openai")):
        with pytest.raises(LLMError) as exc_info:
            llm_client.execute("Test prompt", "gpt-5")
        assert "Request timeout" in str(exc_info.value)
        assert "gpt-5" in str(exc_info.value)

def test_execute_api_error(llm_client):
    with patch("dakora.llm.client.completion", side_effect=APIError(status_code=500, message="API error occurred", llm_provider="openai", model="gpt-5")):
        with pytest.raises(LLMError) as exc_info:
            llm_client.execute("Test prompt", "gpt-5")
        assert "API error" in str(exc_info.value)

def test_execute_unexpected_error(llm_client):
    with patch("dakora.llm.client.completion", side_effect=Exception("Unexpected error")):
        with pytest.raises(LLMError) as exc_info:
            llm_client.execute("Test prompt", "gpt-5")
        assert "Unexpected error" in str(exc_info.value)

def test_execute_latency_measurement(llm_client, mock_litellm_response):
    with patch("dakora.llm.client.completion", return_value=mock_litellm_response):
        result = llm_client.execute("Test prompt", "gpt-5")
        assert isinstance(result.latency_ms, int)
        assert result.latency_ms >= 0

def test_execute_with_temperature_param(llm_client, mock_litellm_response):
    with patch("dakora.llm.client.completion", return_value=mock_litellm_response) as mock_completion:
        result = llm_client.execute("Test prompt", "gpt-5", temperature=0.7)

        mock_completion.assert_called_once()
        call_kwargs = mock_completion.call_args[1]
        assert call_kwargs["temperature"] == 0.7
        assert call_kwargs["model"] == "gpt-5"

def test_execute_with_max_tokens_param(llm_client, mock_litellm_response):
    with patch("dakora.llm.client.completion", return_value=mock_litellm_response) as mock_completion:
        result = llm_client.execute("Test prompt", "gpt-5", max_tokens=500)

        mock_completion.assert_called_once()
        call_kwargs = mock_completion.call_args[1]
        assert call_kwargs["max_tokens"] == 500

def test_execute_with_reasoning_param(llm_client, mock_litellm_response):
    with patch("dakora.llm.client.completion", return_value=mock_litellm_response) as mock_completion:
        result = llm_client.execute(
            "Test prompt",
            "gpt-5",
            reasoning={"effort": "low"}
        )

        mock_completion.assert_called_once()
        call_kwargs = mock_completion.call_args[1]
        assert call_kwargs["reasoning"] == {"effort": "low"}

def test_execute_with_conversation_history(llm_client, mock_litellm_response):
    with patch("dakora.llm.client.completion", return_value=mock_litellm_response) as mock_completion:
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is Python?"},
            {"role": "assistant", "content": "Python is a programming language."},
            {"role": "user", "content": "Tell me more about it."}
        ]

        result = llm_client.execute("", "gpt-5", messages=messages)

        mock_completion.assert_called_once()
        call_kwargs = mock_completion.call_args[1]
        assert call_kwargs["messages"] == messages

def test_execute_with_multiple_params(llm_client, mock_litellm_response):
    with patch("dakora.llm.client.completion", return_value=mock_litellm_response) as mock_completion:
        result = llm_client.execute(
            "Test prompt",
            "gpt-5",
            temperature=0.8,
            max_tokens=1000,
            top_p=0.95,
            frequency_penalty=0.5,
            presence_penalty=0.3
        )

        mock_completion.assert_called_once()
        call_kwargs = mock_completion.call_args[1]
        assert call_kwargs["temperature"] == 0.8
        assert call_kwargs["max_tokens"] == 1000
        assert call_kwargs["top_p"] == 0.95
        assert call_kwargs["frequency_penalty"] == 0.5
        assert call_kwargs["presence_penalty"] == 0.3

def test_execute_with_custom_timeout(llm_client, mock_litellm_response):
    with patch("dakora.llm.client.completion", return_value=mock_litellm_response) as mock_completion:
        result = llm_client.execute("Test prompt", "gpt-5", timeout=60)

        mock_completion.assert_called_once()
        call_kwargs = mock_completion.call_args[1]
        assert call_kwargs["timeout"] == 60

def test_execute_default_timeout(llm_client, mock_litellm_response):
    with patch("dakora.llm.client.completion", return_value=mock_litellm_response) as mock_completion:
        result = llm_client.execute("Test prompt", "gpt-5")

        mock_completion.assert_called_once()
        call_kwargs = mock_completion.call_args[1]
        assert call_kwargs["timeout"] == 120

def test_execute_messages_override_prompt(llm_client, mock_litellm_response):
    with patch("dakora.llm.client.completion", return_value=mock_litellm_response) as mock_completion:
        custom_messages = [{"role": "user", "content": "Custom message"}]
        result = llm_client.execute("Ignored prompt", "gpt-5", messages=custom_messages)

        mock_completion.assert_called_once()
        call_kwargs = mock_completion.call_args[1]
        assert call_kwargs["messages"] == custom_messages