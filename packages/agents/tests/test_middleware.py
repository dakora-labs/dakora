"""Tests for DakoraTraceMiddleware"""

import asyncio
import pytest
from unittest.mock import MagicMock
from agent_framework import ChatContext, ChatMessage, Role

from dakora_agents.maf import DakoraTraceMiddleware


@pytest.mark.asyncio
class TestDakoraTraceMiddleware:
    """Test suite for DakoraTraceMiddleware"""
    
    async def test_middleware_initialization(self, mock_dakora_client, project_id):
        """Test middleware can be initialized with required parameters"""
        middleware = DakoraTraceMiddleware(
            dakora_client=mock_dakora_client,
            project_id=project_id,
        )
        
        assert middleware.dakora == mock_dakora_client
        assert middleware.project_id == project_id
        assert middleware.agent_id is None
        assert middleware.session_id is not None  # Auto-generated
    
    async def test_middleware_with_optional_params(
        self, mock_dakora_client, project_id, agent_id, session_id
    ):
        """Test middleware initialization with all optional parameters"""
        middleware = DakoraTraceMiddleware(
            dakora_client=mock_dakora_client,
            project_id=project_id,
            agent_id=agent_id,
            session_id=session_id,
        )
        
        assert middleware.agent_id == agent_id
        assert middleware.session_id == session_id
    
    async def test_process_adds_trace_metadata(
        self, mock_dakora_client, project_id, sample_chat_context
    ):
        """Test that process() adds trace metadata to context"""
        middleware = DakoraTraceMiddleware(
            dakora_client=mock_dakora_client,
            project_id=project_id,
        )
        
        async def mock_next(ctx: ChatContext) -> None:
            # Simulate LLM response
            ctx.messages.append(ChatMessage(role=Role.ASSISTANT, text="Response"))
        
        await middleware.process(sample_chat_context, mock_next)
        
        # Check trace metadata was added
        assert "dakora_trace_id" in sample_chat_context.metadata
        assert "dakora_session_id" in sample_chat_context.metadata
        assert sample_chat_context.metadata["dakora_session_id"] == middleware.session_id
    
    async def test_process_creates_trace(
        self, mock_dakora_client, project_id, sample_chat_context
    ):
        """Test that process() calls dakora.traces.create()"""
        middleware = DakoraTraceMiddleware(
            dakora_client=mock_dakora_client,
            project_id=project_id,
        )
        
        async def mock_next(ctx: ChatContext) -> None:
            ctx.messages.append(ChatMessage(role=Role.ASSISTANT, text="Response"))
        
        await middleware.process(sample_chat_context, mock_next)
        
        # Give async logging a moment to complete
        await asyncio.sleep(0.1)
        
        # Verify trace was created
        mock_dakora_client.traces.create.assert_called_once()
        call_args = mock_dakora_client.traces.create.call_args[1]
        
        assert "trace_id" in call_args
        assert call_args["session_id"] == middleware.session_id
        assert "conversation_history" in call_args
        assert "latency_ms" in call_args
    
    async def test_process_with_template_metadata(
        self, mock_dakora_client, project_id
    ):
        """Test that template metadata from messages is captured"""
        from agent_framework import ChatOptions
        
        middleware = DakoraTraceMiddleware(
            dakora_client=mock_dakora_client,
            project_id=project_id,
        )
        
        # Create message with Dakora context
        message = ChatMessage(role=Role.USER, text="Hello")
        message._dakora_context = {
            "prompt_id": "greeting-prompt",
            "version": "1.0",
            "inputs": {"name": "Alice"},
            "metadata": {"category": "greeting"}
        }
        
        mock_chat_client = MagicMock()
        context = ChatContext(
            messages=[message],
            metadata={},
            chat_client=mock_chat_client,
            chat_options=ChatOptions()
        )
        
        async def mock_next(ctx: ChatContext) -> None:
            ctx.messages.append(ChatMessage(role=Role.ASSISTANT, text="Hi Alice!"))
        
        await middleware.process(context, mock_next)
        await asyncio.sleep(0.1)
        
        # Verify template usage was tracked
        call_args = mock_dakora_client.traces.create.call_args[1]
        assert "template_usages" in call_args
        assert len(call_args["template_usages"]) == 1
        assert call_args["template_usages"][0]["prompt_id"] == "greeting-prompt"
    
    async def test_process_calculates_latency(
        self, mock_dakora_client, project_id, sample_chat_context
    ):
        """Test that latency is calculated correctly"""
        middleware = DakoraTraceMiddleware(
            dakora_client=mock_dakora_client,
            project_id=project_id,
        )
        
        async def mock_next(ctx: ChatContext) -> None:
            await asyncio.sleep(0.05)  # Simulate 50ms LLM call
            ctx.messages.append(ChatMessage(role=Role.ASSISTANT, text="Response"))
        
        await middleware.process(sample_chat_context, mock_next)
        await asyncio.sleep(0.1)
        
        call_args = mock_dakora_client.traces.create.call_args[1]
        assert call_args["latency_ms"] >= 50  # Should be at least 50ms
    
    async def test_process_includes_agent_id_when_set(
        self, mock_dakora_client, project_id, agent_id, sample_chat_context
    ):
        """Test that agent_id is included in trace when provided"""
        middleware = DakoraTraceMiddleware(
            dakora_client=mock_dakora_client,
            project_id=project_id,
            agent_id=agent_id,
        )
        
        async def mock_next(ctx: ChatContext) -> None:
            ctx.messages.append(ChatMessage(role=Role.ASSISTANT, text="Response"))
        
        await middleware.process(sample_chat_context, mock_next)
        await asyncio.sleep(0.1)
        
        call_args = mock_dakora_client.traces.create.call_args[1]
        assert call_args.get("agent_id") == agent_id
    
    async def test_process_handles_exceptions_gracefully(
        self, mock_dakora_client, project_id, sample_chat_context
    ):
        """Test that middleware doesn't break if trace creation fails"""
        # Make traces.create raise an exception
        mock_dakora_client.traces.create.side_effect = Exception("API Error")
        
        middleware = DakoraTraceMiddleware(
            dakora_client=mock_dakora_client,
            project_id=project_id,
        )
        
        async def mock_next(ctx: ChatContext) -> None:
            ctx.messages.append(ChatMessage(role=Role.ASSISTANT, text="Response"))
        
        # Should not raise - middleware should handle errors gracefully
        await middleware.process(sample_chat_context, mock_next)
        await asyncio.sleep(0.1)
        
        # Agent should still work (response was added)
        assert len(sample_chat_context.messages) == 2
    
    async def test_process_preserves_conversation_history(
        self, mock_dakora_client, project_id
    ):
        """Test that full conversation history is captured"""
        from agent_framework import ChatOptions
        
        middleware = DakoraTraceMiddleware(
            dakora_client=mock_dakora_client,
            project_id=project_id,
        )
        
        mock_chat_client = MagicMock()
        context = ChatContext(
            messages=[
                ChatMessage(role=Role.SYSTEM, text="You are helpful"),
                ChatMessage(role=Role.USER, text="Hello"),
            ],
            metadata={},
            chat_client=mock_chat_client,
            chat_options=ChatOptions()
        )
        
        async def mock_next(ctx: ChatContext) -> None:
            ctx.messages.append(ChatMessage(role=Role.ASSISTANT, text="Hi there!"))
        
        await middleware.process(context, mock_next)
        await asyncio.sleep(0.1)
        
        call_args = mock_dakora_client.traces.create.call_args[1]
        history = call_args["conversation_history"]
        
        assert len(history) == 3
        assert history[0]["role"] == "system"
        assert history[1]["role"] == "user"
        assert history[2]["role"] == "assistant"


@pytest.mark.asyncio
class TestMiddlewareHelper:
    """Tests for create_dakora_middleware helper"""
    
    async def test_create_middleware_helper(self, mock_dakora_client, project_id):
        """Test the create_dakora_middleware helper function"""
        from dakora_agents.maf import create_dakora_middleware
        
        middleware = create_dakora_middleware(
            dakora_client=mock_dakora_client,
            project_id=project_id,
        )
        
        assert isinstance(middleware, DakoraTraceMiddleware)
        assert middleware.project_id == project_id
    
    async def test_create_middleware_with_all_params(
        self, mock_dakora_client, project_id, agent_id, session_id
    ):
        """Test helper with all parameters"""
        from dakora_agents.maf import create_dakora_middleware
        
        middleware = create_dakora_middleware(
            dakora_client=mock_dakora_client,
            project_id=project_id,
            agent_id=agent_id,
            session_id=session_id,
        )
        
        assert middleware.agent_id == agent_id
        assert middleware.session_id == session_id
