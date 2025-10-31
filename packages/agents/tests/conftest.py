"""Pytest configuration and fixtures for dakora-agents tests"""

import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_dakora_client():
    """Mock Dakora client for testing"""
    client = MagicMock()
    client.base_url = "http://localhost:8000"
    client.project_id = "test-project-123"
    client._Dakora__api_key = "test-api-key"  # Private attribute
    client.get = AsyncMock(return_value=MagicMock(
        status_code=200,
        json=lambda: {"exceeded": False, "status": "ok"},
        raise_for_status=lambda: None
    ))
    client.prompts = MagicMock()
    client.prompts.render = AsyncMock(return_value=MagicMock(
        text="Test prompt text",
        version="1.0",
        prompt_id="test-prompt",
        inputs={"key": "value"},
        metadata={}
    ))
    return client


@pytest.fixture
def sample_chat_context():
    """Sample ChatContext for testing"""
    from agent_framework import ChatContext, ChatMessage, Role, ChatOptions
    
    # Create a mock chat client
    mock_chat_client = MagicMock()
    mock_chat_client.complete = AsyncMock(return_value=ChatMessage(
        role=Role.ASSISTANT,
        text="Mock response"
    ))
    
    context = ChatContext(
        messages=[
            ChatMessage(role=Role.USER, text="Hello"),
        ],
        metadata={},
        chat_client=mock_chat_client,
        chat_options=ChatOptions()
    )
    return context


@pytest.fixture
def sample_render_result():
    """Sample RenderResult for testing to_message()"""
    result = MagicMock()
    result.text = "Rendered template text"
    result.version = "1.0"
    result.prompt_id = "test-prompt"
    result.inputs = {"user": "Alice"}
    result.metadata = {"category": "greeting"}
    return result


@pytest.fixture
def project_id():
    """Test project ID"""
    return "test-project-123"


@pytest.fixture
def agent_id():
    """Test agent ID"""
    return "test-agent"


@pytest.fixture
def session_id():
    """Test session ID"""
    return "test-session-456"
