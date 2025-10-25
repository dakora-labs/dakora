"""Integration tests for dakora-agents with mock Agent Framework"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock
from agent_framework import ChatAgent, ChatContext, ChatMessage, Role

from dakora_agents.maf import create_dakora_middleware, to_message


@pytest.mark.asyncio
class TestIntegration:
    """Integration tests simulating real usage patterns"""
    
    async def test_agent_with_middleware(self, mock_dakora_client, project_id):
        """Test that middleware works with ChatAgent"""
        middleware = create_dakora_middleware(
            dakora_client=mock_dakora_client,
            project_id=project_id,
            agent_id="test-agent",
        )
        
        # Create a mock chat client
        mock_chat_client = MagicMock()
        mock_chat_client.complete = AsyncMock(return_value=ChatMessage(
            role=Role.ASSISTANT,
            text="Hello! How can I help you?"
        ))
        
        # Create agent with middleware
        agent = ChatAgent(
            name="TestAgent",
            chat_client=mock_chat_client,
            instructions="You are a test assistant",
            middleware=[middleware]
        )
        
        # Verify middleware is attached
        assert middleware in agent.middleware
    
    async def test_template_workflow(self, mock_dakora_client, project_id):
        """Test complete workflow: render template -> to_message -> agent"""
        from agent_framework import ChatOptions
        
        # Render template
        render_result = await mock_dakora_client.prompts.render(
            "greeting",
            {"name": "Alice"}
        )
        
        # Convert to message
        message = to_message(render_result, role=Role.SYSTEM)
        
        # Verify message has context
        assert hasattr(message, "_dakora_context")
        assert message._dakora_context["prompt_id"] == "test-prompt"
        
        # Create middleware
        middleware = create_dakora_middleware(
            dakora_client=mock_dakora_client,
            project_id=project_id,
        )
        
        # Simulate agent processing
        mock_chat_client = MagicMock()
        context = ChatContext(
            messages=[message],
            metadata={},
            chat_client=mock_chat_client,
            chat_options=ChatOptions()
        )
        
        async def mock_next(ctx: ChatContext) -> None:
            ctx.messages.append(ChatMessage(role=Role.ASSISTANT, text="Response"))
        
        await middleware.process(context, mock_next)
        await asyncio.sleep(0.1)
        
        # Verify trace was created with template info
        assert mock_dakora_client.traces.create.called
        call_args = mock_dakora_client.traces.create.call_args[1]
        assert len(call_args["template_usages"]) == 1
    
    async def test_multi_turn_conversation(self, mock_dakora_client, project_id):
        """Test middleware tracks multi-turn conversations with same session"""
        from agent_framework import ChatOptions
        
        session_id = "conversation-123"
        
        middleware = create_dakora_middleware(
            dakora_client=mock_dakora_client,
            project_id=project_id,
            session_id=session_id,
        )
        
        mock_chat_client = MagicMock()
        
        # First turn
        context1 = ChatContext(
            messages=[ChatMessage(role=Role.USER, text="Hello")],
            metadata={},
            chat_client=mock_chat_client,
            chat_options=ChatOptions()
        )
        
        async def mock_next(ctx: ChatContext) -> None:
            ctx.messages.append(ChatMessage(role=Role.ASSISTANT, text="Hi!"))
        
        await middleware.process(context1, mock_next)
        await asyncio.sleep(0.1)
        
        # Second turn
        context2 = ChatContext(
            messages=[
                ChatMessage(role=Role.USER, text="Hello"),
                ChatMessage(role=Role.ASSISTANT, text="Hi!"),
                ChatMessage(role=Role.USER, text="How are you?"),
            ],
            metadata={},
            chat_client=mock_chat_client,
            chat_options=ChatOptions()
        )
        
        await middleware.process(context2, mock_next)
        await asyncio.sleep(0.1)
        
        # Both calls should use same session_id
        assert mock_dakora_client.traces.create.call_count == 2
        
        call1_args = mock_dakora_client.traces.create.call_args_list[0][1]
        call2_args = mock_dakora_client.traces.create.call_args_list[1][1]
        
        assert call1_args["session_id"] == session_id
        assert call2_args["session_id"] == session_id
    
    async def test_multi_agent_workflow(self, mock_dakora_client, project_id):
        """Test multiple agents sharing same session"""
        from agent_framework import ChatOptions
        
        session_id = "workflow-456"
        
        # Agent 1
        agent1_middleware = create_dakora_middleware(
            dakora_client=mock_dakora_client,
            project_id=project_id,
            agent_id="researcher",
            session_id=session_id,
        )
        
        # Agent 2
        agent2_middleware = create_dakora_middleware(
            dakora_client=mock_dakora_client,
            project_id=project_id,
            agent_id="writer",
            session_id=session_id,
        )
        
        mock_chat_client = MagicMock()
        
        # Both agents process messages
        context1 = ChatContext(
            messages=[ChatMessage(role=Role.USER, text="Research AI")],
            metadata={},
            chat_client=mock_chat_client,
            chat_options=ChatOptions()
        )
        
        context2 = ChatContext(
            messages=[ChatMessage(role=Role.USER, text="Write article")],
            metadata={},
            chat_client=mock_chat_client,
            chat_options=ChatOptions()
        )
        
        async def mock_next(ctx: ChatContext) -> None:
            ctx.messages.append(ChatMessage(role=Role.ASSISTANT, text="Done"))
        
        await agent1_middleware.process(context1, mock_next)
        await agent2_middleware.process(context2, mock_next)
        await asyncio.sleep(0.1)
        
        # Both should share session but have different agent_ids
        assert mock_dakora_client.traces.create.call_count == 2
        
        call1 = mock_dakora_client.traces.create.call_args_list[0][1]
        call2 = mock_dakora_client.traces.create.call_args_list[1][1]
        
        assert call1["session_id"] == session_id
        assert call2["session_id"] == session_id
        assert call1.get("agent_id") == "researcher"
        assert call2.get("agent_id") == "writer"
