"""Tests for DakoraTraceMiddleware with OTLP architecture"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from agent_framework import ChatContext, ChatMessage, Role

from dakora_agents.maf import DakoraTraceMiddleware


@pytest.mark.asyncio
class TestDakoraTraceMiddleware:
    """Test suite for DakoraTraceMiddleware"""

    async def test_middleware_initialization(self, mock_dakora_client):
        """Test middleware can be initialized"""
        middleware = DakoraTraceMiddleware(
            dakora_client=mock_dakora_client,
            budget_check_cache_ttl=30,
        )

        assert middleware.dakora == mock_dakora_client
        assert middleware.budget_check_cache_ttl == 30

    async def test_budget_check_allows_execution_when_under_budget(self, mock_dakora_client, sample_chat_context):
        """Test that execution proceeds when budget is not exceeded"""
        # Mock budget check to return under budget
        mock_dakora_client.get = AsyncMock(return_value=MagicMock(
            status_code=200,
            json=lambda: {"exceeded": False, "status": "ok"}
        ))

        middleware = DakoraTraceMiddleware(dakora_client=mock_dakora_client)

        executed = False

        async def mock_next(ctx: ChatContext) -> None:
            nonlocal executed
            executed = True
            ctx.messages.append(ChatMessage(role=Role.ASSISTANT, text="Response"))

        await middleware.process(sample_chat_context, mock_next)

        assert executed is True
        assert len(sample_chat_context.messages) == 2

    async def test_budget_check_blocks_execution_when_exceeded_strict(self, mock_dakora_client, sample_chat_context):
        """Test that execution is blocked when budget exceeded in strict mode"""
        # Mock budget check to return exceeded with strict enforcement
        mock_dakora_client.get = AsyncMock(return_value=MagicMock(
            status_code=200,
            json=lambda: {
                "exceeded": True,
                "enforcement_mode": "strict",
                "budget_usd": 10.0,
                "current_spend_usd": 12.0
            }
        ))

        middleware = DakoraTraceMiddleware(dakora_client=mock_dakora_client, enable_budget_check=True)

        executed = False

        async def mock_next(ctx: ChatContext) -> None:
            nonlocal executed
            executed = True

        await middleware.process(sample_chat_context, mock_next)

        assert executed is False  # Should not execute
        assert sample_chat_context.terminate is True  # Should terminate
        assert sample_chat_context.result is not None  # Should have error response

    async def test_budget_check_allows_execution_when_exceeded_alert(self, mock_dakora_client, sample_chat_context):
        """Test that execution proceeds when budget exceeded in alert mode"""
        # Mock budget check to return exceeded with alert enforcement
        mock_dakora_client.get = AsyncMock(return_value=MagicMock(
            status_code=200,
            json=lambda: {
                "exceeded": True,
                "enforcement_mode": "alert",
                "budget_usd": 10.0,
                "current_spend_usd": 12.0
            }
        ))

        middleware = DakoraTraceMiddleware(dakora_client=mock_dakora_client)

        executed = False

        async def mock_next(ctx: ChatContext) -> None:
            nonlocal executed
            executed = True
            ctx.messages.append(ChatMessage(role=Role.ASSISTANT, text="Response"))

        await middleware.process(sample_chat_context, mock_next)

        assert executed is True  # Should execute despite budget exceeded
        assert len(sample_chat_context.messages) == 2

    async def test_budget_check_uses_cache(self, mock_dakora_client, sample_chat_context):
        """Test that budget check uses TTL cache"""
        # Mock budget check
        mock_dakora_client.get = AsyncMock(return_value=MagicMock(
            status_code=200,
            json=lambda: {"exceeded": False, "status": "ok"}
        ))

        middleware = DakoraTraceMiddleware(
            dakora_client=mock_dakora_client,
            enable_budget_check=True,
            budget_check_cache_ttl=30
        )

        async def mock_next(ctx: ChatContext) -> None:
            ctx.messages.append(ChatMessage(role=Role.ASSISTANT, text="Response"))

        # First call - should hit API
        await middleware.process(sample_chat_context, mock_next)
        assert mock_dakora_client.get.call_count == 1

        # Second call - should use cache
        await middleware.process(sample_chat_context, mock_next)
        assert mock_dakora_client.get.call_count == 1  # Still 1, didn't call again

    async def test_budget_check_fail_open(self, mock_dakora_client, sample_chat_context):
        """Test that budget check fails open when API call fails"""
        # Mock budget check to raise exception
        mock_dakora_client.get = AsyncMock(side_effect=Exception("API Error"))

        middleware = DakoraTraceMiddleware(dakora_client=mock_dakora_client)

        executed = False

        async def mock_next(ctx: ChatContext) -> None:
            nonlocal executed
            executed = True

        await middleware.process(sample_chat_context, mock_next)

        assert executed is True  # Should execute despite error (fail-open)

    async def test_sets_dakora_attributes_on_span(self, mock_dakora_client, sample_chat_context):
        """Test that middleware sets dakora.* attributes on current span"""
        mock_span = MagicMock()
        mock_span.is_recording.return_value = True

        # Create a mock trace module
        mock_trace = MagicMock()
        mock_trace.get_current_span.return_value = mock_span

        with patch('opentelemetry.trace', mock_trace):
            middleware = DakoraTraceMiddleware(dakora_client=mock_dakora_client)

            # Add model to chat client
            sample_chat_context.chat_client.model_id = "gpt-4"

            async def mock_next(ctx: ChatContext) -> None:
                pass

            await middleware.process(sample_chat_context, mock_next)

            # Verify dakora.model was set
            mock_span.set_attribute.assert_any_call("dakora.model", "gpt-4")

    async def test_extracts_template_contexts_from_messages(self, mock_dakora_client):
        """Test that middleware extracts template contexts from messages"""
        from agent_framework import ChatOptions

        mock_span = MagicMock()
        mock_span.is_recording.return_value = True

        # Create a mock trace module
        mock_trace = MagicMock()
        mock_trace.get_current_span.return_value = mock_span

        # Create message with dakora context
        message = ChatMessage(role=Role.USER, text="Hello")
        message._dakora_context = {
            "prompt_id": "greeting",
            "version": "1.0",
            "inputs": {"name": "Alice"},
            "metadata": {}
        }

        mock_chat_client = MagicMock()
        context = ChatContext(
            messages=[message],
            metadata={},
            chat_client=mock_chat_client,
            chat_options=ChatOptions()
        )

        with patch('opentelemetry.trace', mock_trace):
            middleware = DakoraTraceMiddleware(dakora_client=mock_dakora_client)

            async def mock_next(ctx: ChatContext) -> None:
                pass

            await middleware.process(context, mock_next)

            # Verify template contexts were set as JSON
            calls = [call for call in mock_span.set_attribute.call_args_list
                     if call[0][0] == "dakora.template_contexts"]
            assert len(calls) == 1

            template_contexts_json = calls[0][0][1]
            template_contexts = json.loads(template_contexts_json)
            assert len(template_contexts) == 1
            assert template_contexts[0]["prompt_id"] == "greeting"

    async def test_handles_no_otel_gracefully(self, mock_dakora_client, sample_chat_context):
        """Test that middleware works even if OTEL is not available"""
        # Mock the import to raise ImportError
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == 'opentelemetry' or name.startswith('opentelemetry.'):
                raise ImportError("OTEL not available")
            return real_import(name, *args, **kwargs)

        with patch('builtins.__import__', side_effect=mock_import):
            middleware = DakoraTraceMiddleware(dakora_client=mock_dakora_client)

            executed = False

            async def mock_next(ctx: ChatContext) -> None:
                nonlocal executed
                executed = True

            # Should not raise error
            await middleware.process(sample_chat_context, mock_next)
            assert executed is True